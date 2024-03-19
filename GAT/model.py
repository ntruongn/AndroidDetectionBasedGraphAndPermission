
import torch
import torch.utils
import torch.utils.data
import torch.nn as nn
import enum
# Support for 3 different GAT implementations - we'll profile each one of these in playground.py
class LayerType(enum.Enum):
    IMP1 = 0,
    IMP2 = 1,
    IMP3 = 2


class GAT(nn.Module):
    '''
    Baseline Graph Convolutional Network with a stack of Graph Convolution Layers and global pooling over nodes.
    '''
    def __init__(self, num_of_layers, num_heads_per_layer, num_features_per_layer, add_skip_connection=True, bias=True,
                 dropout=0.6, layer_type=LayerType.IMP3, log_attention_weights=False, bnorm=False):
        super(GAT, self).__init__()
        # self.device = device
        assert num_of_layers == len(num_heads_per_layer) == len(num_features_per_layer) - 1, f'Enter valid arch params.'

        GATLayer = get_layer_type(layer_type)  # fetch one of 3 available implementations
        num_heads_per_layer = [1] + num_heads_per_layer  # trick - so that I can nicely create GAT layers below

        gat_layers = []  # collect GAT layers
        for i in range(num_of_layers):
            layer = GATLayer(
                num_in_features=num_features_per_layer[i] * num_heads_per_layer[i],  # consequence of concatenation
                num_out_features=num_features_per_layer[i + 1],
                num_of_heads=num_heads_per_layer[i + 1],
                concat=True if i < num_of_layers - 1 else False,  # last GAT layer does mean avg, the others do concat
                activation=nn.ELU() if i < num_of_layers - 1 else None,  # last layer just outputs raw scores
                dropout_prob=dropout,
                add_skip_connection=add_skip_connection,
                bias=bias,
                log_attention_weights=log_attention_weights,
                bnorm=bnorm
            )
            gat_layers.append(layer)
        self.gat_net = nn.Sequential(
            *gat_layers,
        )

        # GCN后的全连接层
        fc_gcn0 = []
        if dropout > 0:
            fc_gcn0.append(nn.Dropout(p=dropout))
        fc_gcn0.append(nn.ReLU(inplace=True))
        n_last = num_features_per_layer[-1]
        fc_gcn0.append(nn.Linear(n_last, 128))
        self.fc_gcn0 = nn.Sequential(*fc_gcn0)

        # Permission的全连接层
        fc_permission0 = []
        if dropout > 0:
            fc_permission0.append(nn.Dropout(p=dropout))
        
        fc_permission0.append(nn.Linear(59, 32))
        fc_permission0.append(nn.ReLU(inplace=True))
        self.fc_permission0 = nn.Sequential(*fc_permission0)

        ##################### 融合层1
        # 双特征拼接全连接层
        fc_mult1 = []
        if dropout > 0:
            fc_mult1.append(nn.Dropout(p=dropout))
        fc_mult1.append(nn.ReLU(inplace=True))
        fc_mult1.append(nn.Linear(128 + 32, 128))
        self.fc_mult1 = nn.Sequential(*fc_mult1)

        # GCN后的全连接层
        fc_gcn1 = []
        if dropout > 0:
            fc_gcn1.append(nn.Dropout(p=dropout))
        fc_gcn1.append(nn.ReLU(inplace=True))
        fc_gcn1.append(nn.Linear(128, 64))
        self.fc_gcn1 = nn.Sequential(*fc_gcn1)

        # Permission的全连接层
        fc_permission1 = []
        if dropout > 0:
            fc_permission1.append(nn.Dropout(p=dropout))
        fc_permission1.append(nn.Linear(32, 32))
        fc_permission1.append(nn.ReLU(inplace=True))
        self.fc_permission1 = nn.Sequential(*fc_permission1)



        ################## 融合层2
        # 双特征拼接全连接层
        fc_mult2 = []
        if dropout > 0:
            fc_mult2.append(nn.Dropout(p=dropout))
        fc_mult2.append(nn.ReLU(inplace=True))
        fc_mult2.append(nn.Linear(64 + 128 + 32, 64))
        self.fc_mult2 = nn.Sequential(*fc_mult2)
        # GCN后的全连接层
        fc_gcn2 = []
        if dropout > 0:
            fc_gcn2.append(nn.Dropout(p=dropout))
        fc_gcn2.append(nn.ReLU(inplace=True))
        fc_gcn2.append(nn.Linear(64, 32))
        self.fc_gcn2 = nn.Sequential(*fc_gcn2)

        # Permission的全连接层
        fc_permission2 = []
        if dropout > 0:
            fc_permission2.append(nn.Dropout(p=dropout))
        fc_permission2.append(nn.Linear(32, 32))
        fc_permission2.append(nn.ReLU(inplace=True))
        self.fc_permission2 = nn.Sequential(*fc_permission2)


        # 输出后全连接层
        fc_final = []
        if dropout > 0:
            fc_final.append(nn.Dropout(p=dropout))
        fc_final.append(nn.Linear(32 + 64 + 32, 64))
        self.fc_final = nn.Sequential(*fc_final)

        # 输出后全连接层
        fc_out = []
        if dropout > 0:
            fc_out.append(nn.Dropout(p=dropout))
        fc_out.append(nn.Linear(64, 2))
        self.fc_out = nn.Sequential(*fc_out)

    def forward(self, data):
        # 图卷积到fc_gcn0
        x = self.gat_net(data[:2])[0]
        # print(x.shape)
        # raise Exception
        x = torch.max(x, dim=1)[0].squeeze()  # max pooling over nodes (usually performs better than average)
        # raise Exception
        x = self.fc_gcn0(x)
        if len(x.shape) == 1:
            x = x.unsqueeze(0)
        # permission全连接
        x_ = self.fc_permission0(data[5])
        
        # raise Exception
        # 融合层1

        mu = self.fc_mult1(torch.cat((x, x_), 1))
        x = self.fc_gcn1(x)
        x_ = self.fc_permission1(x_)

        # 融合层2
        mu = self.fc_mult2(torch.cat((x, mu, x_), 1))
        x = self.fc_gcn2(x)
        x_ = self.fc_permission2(x_)

        # 输出层
        out = self.fc_final(torch.cat((x, mu, x_), 1))
        out = self.fc_out(out)

        return out


class GATLayer(torch.nn.Module):
    """
    Base class for all implementations as there is much code that would otherwise be copy/pasted.

    """

    head_dim = 1

    def __init__(self, num_in_features, num_out_features, num_of_heads, layer_type, concat=True, activation=nn.ELU(),
                 dropout_prob=0.6, add_skip_connection=True, bias=True, log_attention_weights=False):

        super().__init__()

        # Saving these as we'll need them in forward propagation in children layers (imp1/2/3)
        self.num_of_heads = num_of_heads
        self.num_out_features = num_out_features
        self.concat = concat  # whether we should concatenate or average the attention heads
        self.add_skip_connection = add_skip_connection

        #
        # Trainable weights: linear projection matrix (denoted as "W" in the paper), attention target/source
        # (denoted as "a" in the paper) and bias (not mentioned in the paper but present in the official GAT repo)
        #

        if layer_type == LayerType.IMP1:
            # Experimenting with different options to see what is faster (tip: focus on 1 implementation at a time)
            self.proj_param = nn.Parameter(torch.Tensor(num_of_heads, num_in_features, num_out_features))
        else:
            # You can treat this one matrix as num_of_heads independent W matrices
            self.linear_proj = nn.Linear(num_in_features, num_of_heads * num_out_features, bias=False)

        # After we concatenate target node (node i) and source node (node j) we apply the additive scoring function
        # which gives us un-normalized score "e". Here we split the "a" vector - but the semantics remain the same.

        # Basically instead of doing [x, y] (concatenation, x/y are node feature vectors) and dot product with "a"
        # we instead do a dot product between x and "a_left" and y and "a_right" and we sum them up
        self.scoring_fn_target = nn.Parameter(torch.Tensor(1, num_of_heads, num_out_features))
        self.scoring_fn_source = nn.Parameter(torch.Tensor(1, num_of_heads, num_out_features))

        if layer_type == LayerType.IMP1:  # simple reshape in the case of implementation 1
            self.scoring_fn_target = nn.Parameter(self.scoring_fn_target.reshape(num_of_heads, num_out_features, 1))
            self.scoring_fn_source = nn.Parameter(self.scoring_fn_source.reshape(num_of_heads, num_out_features, 1))

        # Bias is definitely not crucial to GAT - feel free to experiment (I pinged the main author, Petar, on this one)
        if bias and concat:
            self.bias = nn.Parameter(torch.Tensor(num_of_heads * num_out_features))
        elif bias and not concat:
            self.bias = nn.Parameter(torch.Tensor(num_out_features))
        else:
            self.register_parameter('bias', None)

        if add_skip_connection:
            self.skip_proj = nn.Linear(num_in_features, num_of_heads * num_out_features, bias=False)
        else:
            self.register_parameter('skip_proj', None)

        #
        # End of trainable weights
        #

        self.leakyReLU = nn.LeakyReLU(0.2)  # using 0.2 as in the paper, no need to expose every setting
        self.softmax = nn.Softmax(dim=-1)  # -1 stands for apply the log-softmax along the last dimension
        self.activation = activation
        # Probably not the nicest design but I use the same module in 3 locations, before/after features projection
        # and for attention coefficients. Functionality-wise it's the same as using independent modules.
        self.dropout = nn.Dropout(p=dropout_prob)

        self.log_attention_weights = log_attention_weights  # whether we should log the attention weights
        self.attention_weights = None  # for later visualization purposes, I cache the weights here

        self.init_params(layer_type)

    def init_params(self, layer_type):
        """
        The reason we're using Glorot (aka Xavier uniform) initialization is because it's a default TF initialization:
            https://stackoverflow.com/questions/37350131/what-is-the-default-variable-initializer-in-tensorflow

        The original repo was developed in TensorFlow (TF) and they used the default initialization.
        Feel free to experiment - there may be better initializations depending on your problem.

        """
        nn.init.xavier_uniform_(self.proj_param if layer_type == LayerType.IMP1 else self.linear_proj.weight)
        nn.init.xavier_uniform_(self.scoring_fn_target)
        nn.init.xavier_uniform_(self.scoring_fn_source)

        if self.bias is not None:
            torch.nn.init.zeros_(self.bias)

    def skip_concat_bias(self, attention_coefficients, in_nodes_features, out_nodes_features):
        if self.log_attention_weights:  # potentially log for later visualization in playground.py
            self.attention_weights = attention_coefficients

        # if the tensor is not contiguously stored in memory we'll get an error after we try to do certain ops like view
        # only imp1 will enter this one
        if not out_nodes_features.is_contiguous():
            out_nodes_features = out_nodes_features.contiguous()

        if self.add_skip_connection:  # add skip or residual connection
            if out_nodes_features.shape[-1] == in_nodes_features.shape[-1]:  # if FIN == FOUT
                # unsqueeze does this: (N, FIN) -> (N, 1, FIN), out features are (N, NH, FOUT) so 1 gets broadcast to NH
                # thus we're basically copying input vectors NH times and adding to processed vectors
                out_nodes_features += in_nodes_features.unsqueeze(1)
            else:
                # FIN != FOUT so we need to project input feature vectors into dimension that can be added to output
                # feature vectors. skip_proj adds lots of additional capacity which may cause overfitting.
                out_nodes_features += self.skip_proj(in_nodes_features).view(-1, self.num_of_heads, self.num_out_features)
        # print(self.concat)
        if self.concat:
            # shape = (N, NH, FOUT) -> (N, NH*FOUT)
            out_nodes_features = out_nodes_features.view(-1, self.num_of_heads * self.num_out_features)
        else:
            # shape = (N, NH, FOUT) -> (N, FOUT)
            out_nodes_features = out_nodes_features.mean(dim=self.head_dim)

        if self.bias is not None:
            out_nodes_features += self.bias

        return out_nodes_features if self.activation is None else self.activation(out_nodes_features)


class GATLayerImp2(GATLayer):
    """
        Implementation #2 was inspired by the official GAT implementation: https://github.com/PetarV-/GAT

        It's conceptually simpler than implementation #3 but computationally much less efficient.

        Note: this is the naive implementation not the sparse one and it's only suitable for a transductive setting.
        It would be fairly easy to make it work in the inductive setting as well but the purpose of this layer
        is more educational since it's way less efficient than implementation 3.

    """

    def __init__(self, num_in_features, num_out_features, num_of_heads, concat=True, activation=nn.ELU(),
                 dropout_prob=0.6, add_skip_connection=True, bias=True, log_attention_weights=False, bnorm=False):

        super().__init__(num_in_features, num_out_features, num_of_heads, LayerType.IMP2, concat, activation, dropout_prob,
                         add_skip_connection, bias, log_attention_weights)
        self.bnorm = bnorm
        if self.bnorm:
            bnorm_features = num_of_heads * num_out_features if concat else num_out_features
            self.bn = nn.BatchNorm1d(bnorm_features)

    def forward(self, data):
        #
        # Step 1: Linear Projection + regularization (using linear layer instead of matmul as in imp1)
        #

        in_nodes_features_in, connectivity_mask_in = data  # unpack data
        # print('=' * 100, in_nodes_features_in.shape)
        # print(len(in_nodes_features_in))
        # raise Exception
        # out_nodes_features_out = torch.zeros([0,])
        # connectivity_mask_out = []
        init_ = False
        for i in range(len(in_nodes_features_in)):

            in_nodes_features = in_nodes_features_in[i]
            connectivity_mask = connectivity_mask_in[i]
            # print(in_nodes_features.shape)
            # print(connectivity_mask.shape)
            # print(i)
            # raise Exception
            num_of_nodes = in_nodes_features.shape[0]
            assert connectivity_mask.shape == (num_of_nodes, num_of_nodes), \
                f'Expected connectivity matrix with shape=({num_of_nodes},{num_of_nodes}), got shape={connectivity_mask.shape}.'

            # shape = (N, FIN) where N - number of nodes in the graph, FIN - number of input features per node
            # We apply the dropout to all of the input node features (as mentioned in the paper)
            in_nodes_features = self.dropout(in_nodes_features)

            # shape = (N, FIN) * (FIN, NH*FOUT) -> (N, NH, FOUT) where NH - number of heads, FOUT - num of output features
            # We project the input node features into NH independent output features (one for each attention head)
            nodes_features_proj = self.linear_proj(in_nodes_features).view(-1, self.num_of_heads, self.num_out_features)

            nodes_features_proj = self.dropout(nodes_features_proj)  # in the official GAT imp they did dropout here as well

            #
            # Step 2: Edge attention calculation (using sum instead of bmm + additional permute calls - compared to imp1)
            #
            # print(nodes_features_proj.shape)
            # Apply the scoring function (* represents element-wise (a.k.a. Hadamard) product)
            # shape = (N, NH, FOUT) * (1, NH, FOUT) -> (N, NH, 1)
            # Optimization note: torch.sum() is as performant as .sum() in my experiments
            scores_source = torch.sum((nodes_features_proj * self.scoring_fn_source), dim=-1, keepdim=True)
            scores_target = torch.sum((nodes_features_proj * self.scoring_fn_target), dim=-1, keepdim=True)
            # print(1, scores_source.shape, scores_target.shape)
            # src shape = (NH, N, 1) and trg shape = (NH, 1, N)
            scores_source = scores_source.transpose(0, 1)
            scores_target = scores_target.permute(1, 2, 0)
            # print(2, scores_source.shape, scores_target.shape)
            # shape = (NH, N, 1) + (NH, 1, N) -> (NH, N, N) with the magic of automatic broadcast <3
            # In Implementation 3 we are much smarter and don't have to calculate all NxN scores! (only E!)
            # Tip: it's conceptually easier to understand what happens here if you delete the NH dimension
            all_scores = self.leakyReLU(scores_source + scores_target)
            # connectivity mask will put -inf on all locations where there are no edges, after applying the softmax
            # this will result in attention scores being computed only for existing edges
            all_attention_coefficients = self.softmax(all_scores + connectivity_mask)
            # print(all_attention_coefficients)

            #
            # Step 3: Neighborhood aggregation (same as in imp1)
            #
            # print(3, nodes_features_proj.shape)
            # batch matrix multiply, shape = (NH, N, N) * (NH, N, FOUT) -> (NH, N, FOUT)
            out_nodes_features = torch.bmm(all_attention_coefficients, nodes_features_proj.transpose(0, 1))
            # print(out_nodes_features[0].shape)
            # print(all_attention_coefficients[0])
            # print(out_nodes_features)
            # print(4, out_nodes_features.shape)
            # Note: watch out here I made a silly mistake of using reshape instead of permute thinking it will
            # end up doing the same thing, but it didn't! The acc on Cora didn't go above 52%! (compared to reported ~82%)
            # shape = (N, NH, FOUT)
            out_nodes_features = out_nodes_features.permute(1, 0, 2)
            #
            # Step 4: Residual/skip connections, concat and bias (same as in imp1)
            #
            # print(5, out_nodes_features.shape)
            out_nodes_features = self.skip_concat_bias(all_attention_coefficients, in_nodes_features, out_nodes_features)
            # print(6, out_nodes_features.shape)
            # print(out_nodes_features.shape, connectivity_mask.shape)
            # raise Exception
            if not init_:
                out_nodes_features_out = out_nodes_features.unsqueeze(0)
                connectivity_mask_out = connectivity_mask.unsqueeze(0)
                init_ = True
            else:
                out_nodes_features_out = torch.cat((out_nodes_features_out,out_nodes_features.unsqueeze(0)), dim = 0)
                connectivity_mask_out = torch.cat((connectivity_mask_out, connectivity_mask.unsqueeze(0)), dim=0)

        # print('====' * 24, out_nodes_features_out.shape)
        if self.bnorm:
            out_nodes_features_out = self.bn(out_nodes_features_out.permute(0, 2, 1)).permute(0, 2, 1)
        return (out_nodes_features_out, connectivity_mask_out)


#
# Helper functions
#
def get_layer_type(layer_type):
    assert isinstance(layer_type, LayerType), f'Expected {LayerType} got {type(layer_type)}.'
    if layer_type == LayerType.IMP2:
        return GATLayerImp2
    else:
        raise Exception(f'Layer type {layer_type} not yet supported.')


class GraphConv(nn.Module):
    '''
    Graph Convolution Layer according to (T. Kipf and M. Welling, ICLR 2017) if K<=1
    Chebyshev Graph Convolution Layer according to (M. Defferrard, X. Bresson, and P. Vandergheynst, NIPS 2017) if K>1
    Additional tricks (power of adjacency matrix and weighted self connections) as in the Graph U-Net paper
    '''

    def __init__(self,
                 in_features,
                 out_features,
                 device,
                 n_relations=1,  # number of relation types (adjacency matrices)
                 K=1,  # GCN is K<=1, else ChebNet
                 activation=None,
                 bnorm=False,
                 adj_sq=False,
                 scale_identity=False):
        super(GraphConv, self).__init__()
        # print('-----------------------------------------')
        # print(in_features)
        # print('_________________________________________')
        # print(K)
        # print('=========================================')
        # print(n_relations)
        # print('+++++++++++++++++++++++++++++++++++++++++')
        # print(out_features)
        # print('/////////////////////////////////////////')
        self.fc = nn.Linear(in_features=in_features * K * n_relations, out_features=out_features)
        self.n_relations = n_relations
        assert K > 0, ('filter scale must be greater than 0', K)
        self.K = K
        self.activation = activation
        self.bnorm = bnorm
        self.device = device
        if self.bnorm:
            self.bn = nn.BatchNorm1d(out_features)
        self.adj_sq = adj_sq
        self.scale_identity = scale_identity

    def chebyshev_basis(self, L, X, K):
        if K > 1:
            Xt = [X]
            Xt.append(torch.bmm(L, X))  # B,N,F
            for k in range(2, K):
                Xt.append(2 * torch.bmm(L, Xt[k - 1]) - Xt[k - 2])  # B,N,F
            Xt = torch.cat(Xt, dim=2)  # B,N,K,F
            return Xt
        else:
            # GCN
            assert K == 1, K
            return torch.bmm(L, X)  # B,N,1,F

    def laplacian_batch(self, A):
        batch, N = A.shape[:2]
        if self.adj_sq:
            A = torch.bmm(A, A)  # use A^2 to increase graph connectivity
        A_hat = A
        if self.K < 2 or self.scale_identity:
            I = torch.eye(N).unsqueeze(0).to(self.device)
            if self.scale_identity:
                I = 2 * I  # increase weight of self connections
            if self.K < 2:
                A_hat = A + I
        D_hat = (torch.sum(A_hat, 1) + 1e-5) ** (-0.5)
        L = D_hat.view(batch, N, 1) * A_hat * D_hat.view(batch, 1, N)
        return L

    def forward(self, data):
        x, A, mask = data[:3]
        # print('in', x.shape, torch.sum(torch.abs(torch.sum(x, 2)) > 0))
        if len(A.shape) == 3:
            A = A.unsqueeze(3)
        x_hat = []
        for rel in range(self.n_relations):
            L = self.laplacian_batch(A[:, :, :, rel])
            x_hat.append(self.chebyshev_basis(L, x, self.K))

        x = self.fc(torch.cat(x_hat, 2))
        # print('-------')
        # print(x.size())
        if len(mask.shape) == 2:
            mask = mask.unsqueeze(2)

        x = x * mask  # to make values of dummy nodes zeros again, otherwise the bias is added after applying self.fc which affects node embeddings in the following layers

        if self.bnorm:
            x = self.bn(x.permute(0, 2, 1)).permute(0, 2, 1)
        if self.activation is not None:
            x = self.activation(x)
        return (x, A, mask)


class GCN(nn.Module):
    '''
    Baseline Graph Convolutional Network with a stack of Graph Convolution Layers and global pooling over nodes.
    '''

    def __init__(self,
                 in_features,
                 out_features,
                 device,
                 filters=[64, 64, 64],
                 K=1,
                 bnorm=False,
                 n_hidden=0,
                 dropout=0.2,
                 adj_sq=False,
                 scale_identity=False):
        super(GCN, self).__init__()
        self.device = device
        # Graph convolution layers
        self.gconv = nn.Sequential(*([GraphConv(in_features=in_features if layer == 0 else filters[layer - 1],
                                                out_features=f,
                                                device=self.device,
                                                K=K,
                                                activation=nn.ReLU(inplace=True),
                                                bnorm=bnorm,
                                                adj_sq=adj_sq,
                                                scale_identity=scale_identity) for layer, f in enumerate(filters)]))

        # GCN后的全连接层
        fc_gcn0 = []
        if dropout > 0:
            fc_gcn0.append(nn.Dropout(p=dropout))
        fc_gcn0.append(nn.ReLU(inplace=True))
        n_last = filters[-1]
        fc_gcn0.append(nn.Linear(n_last, 128))
        self.fc_gcn0 = nn.Sequential(*fc_gcn0)

        # Permission的全连接层
        fc_permission0 = []
        if dropout > 0:
            fc_permission0.append(nn.Dropout(p=dropout))
        fc_permission0.append(nn.Linear(500+59, 128))
        fc_permission0.append(nn.ReLU(inplace=True))
        self.fc_permission0 = nn.Sequential(*fc_permission0)

        ##################### 融合层1
        # 双特征拼接全连接层
        fc_mult1 = []
        if dropout > 0:
            fc_mult1.append(nn.Dropout(p=dropout))
        fc_mult1.append(nn.ReLU(inplace=True))
        fc_mult1.append(nn.Linear(128 + 128, 128))
        self.fc_mult1 = nn.Sequential(*fc_mult1)

        # GCN后的全连接层
        fc_gcn1 = []
        if dropout > 0:
            fc_gcn1.append(nn.Dropout(p=dropout))
        fc_gcn1.append(nn.ReLU(inplace=True))
        fc_gcn1.append(nn.Linear(128, 64))
        self.fc_gcn1 = nn.Sequential(*fc_gcn1)

        # Permission的全连接层
        fc_permission1 = []
        if dropout > 0:
            fc_permission1.append(nn.Dropout(p=dropout))
        fc_permission1.append(nn.Linear(128, 64))
        fc_permission1.append(nn.ReLU(inplace=True))
        self.fc_permission1 = nn.Sequential(*fc_permission1)



        ################## 融合层2
        # 双特征拼接全连接层
        fc_mult2 = []
        if dropout > 0:
            fc_mult2.append(nn.Dropout(p=dropout))
        fc_mult2.append(nn.ReLU(inplace=True))
        fc_mult2.append(nn.Linear(64 + 128 + 64, 64))
        self.fc_mult2 = nn.Sequential(*fc_mult2)
        # GCN后的全连接层
        fc_gcn2 = []
        if dropout > 0:
            fc_gcn2.append(nn.Dropout(p=dropout))
        fc_gcn2.append(nn.ReLU(inplace=True))
        fc_gcn2.append(nn.Linear(64, 32))
        self.fc_gcn2 = nn.Sequential(*fc_gcn2)

        # Permission的全连接层
        fc_permission2 = []
        if dropout > 0:
            fc_permission2.append(nn.Dropout(p=dropout))
        fc_permission2.append(nn.Linear(64, 32))
        fc_permission2.append(nn.ReLU(inplace=True))
        self.fc_permission2 = nn.Sequential(*fc_permission2)


        # 输出后全连接层
        fc_final = []
        if dropout > 0:
            fc_final.append(nn.Dropout(p=dropout))
        fc_final.append(nn.Linear(32 + 64 + 32, 64))
        self.fc_final = nn.Sequential(*fc_final)

        # 输出后全连接层
        fc_out = []
        if dropout > 0:
            fc_out.append(nn.Dropout(p=dropout))
        fc_out.append(nn.Linear(64, out_features))
        self.fc_out = nn.Sequential(*fc_out)

    def forward(self, data):
        # 图卷积到fc_gcn0
        x = self.gconv(data)[0]
        x = torch.max(x, dim=1)[0].squeeze()  # max pooling over nodes (usually performs better than average)
        x = self.fc_gcn0(x)
        # permission全连接
        x_ = self.fc_permission0(data[5])
        # 融合层1
        mu = self.fc_mult1(torch.cat((x, x_), 1))
        x = self.fc_gcn1(x)
        x_ = self.fc_permission1(x_)

        # 融合层2
        mu = self.fc_mult2(torch.cat((x, mu, x_), 1))
        x = self.fc_gcn2(x)
        x_ = self.fc_permission2(x_)

        # 输出层
        out = self.fc_final(torch.cat((x, mu, x_), 1))
        out = self.fc_out(out)

        return out
