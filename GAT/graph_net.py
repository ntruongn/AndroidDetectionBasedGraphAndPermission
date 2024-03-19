import matplotlib

matplotlib.use('agg')
import numpy as np
import time
import torch
import torch.utils
import torch.utils.data
import torch.nn.functional as F
import torch.optim as optim
import torch.optim.lr_scheduler as lr_scheduler
from torch.utils.data import DataLoader
from .GraphData import GraphData
from .DataReader_GAT import DataReader
from .DataReader_GCN import DataReader as DataReaderGCN
# from .model import GAT, GCN  #, GraphUnet, MGCN
from .model import GAT, GCN  #, GraphUnet, MGCN
import sys
sys.path.append('..')
from memory_usage import memory_usage

print('using torch', torch.__version__)
class graph_net:
    args = {}

    def __init_args__(self):
        from .model import LayerType
        self.args['description'] = 'Graph Convolutional Networks'
        self.args['dataset'] = 'AMD_AndroZoo_test'
        self.args['model'] = 'gat' # choices=['gcn', 'gat']
        self.args['lr'] = 0.001 # learning rate
        self.args['lr_decay_steps'] = '5,10,15,20,25,30,35,40,45'#,50,55,60,65,70,75,80,85,90,95'
        self.args['wd'] = 1e-4 # weight decay
        self.args['dropout'] = 0.2 # dropout rate
        self.args['filters'] = '128' # number of filters in each layer
        self.args['filter_scale'] = 1 # filter scale (receptive field size), must be > 0; 1 for GCN, >1 for ChebNet'
        self.args['n_hidden'] = 0 # number of hidden units in a fully connected layer after the last conv layer
        self.args['n_hidden_edge'] = 32 # number of hidden units in a fully connected layer of the edge prediction network
        self.args['epochs'] = 50 # number of epochs
        self.args['batch_size'] = 10 # batch size
        self.args['bn'] = False # use BatchNorm layer
        self.args['threads'] = 0 # number of threads to load data
        self.args['log_interval'] = 10 # interval (number of batches) of logging
        self.args['device'] = 'cuda' # choices=['cuda', 'cpu']
        self.args['seed'] = 1 # random seed
        self.args['shuffle_nodes'] = False # shuffle nodes for debugging
        self.args['adj_sq'] = False # use A^2 instead of A as an adjacency matrix
        self.args['scale_identity'] = False # use 2I instead of I for self connections
        self.args['visualize'] = False # only for unet: save some adjacency matrices and other data as images
        self.args['use_cont_node_attr'] = True # use continuous node attributes in addition to discrete one\
        self.args['use_node_labels'] = False #
        self.args['num_of_layers'] = 1 # GAT专用，表示GAT层数
        self.args['num_heads_per_layer'] = [2] # GAT专用
        self.args['num_features_per_layer'] = [500, 128] # GAT专用，表示每层的特征数量，相当于GCN的filters
        self.args['add_skip_connection'] = True # GAT专用
        self.args['bias'] = True # GAT专用
        self.args['layer_type'] = LayerType.IMP2 # GAT专用
        self.args['log_attention_weights'] = False # GAT专用

        self.args['filters'] = list(map(int, self.args['filters'].split(',')))
        self.args['lr_decay_steps'] = list(map(int, self.args['lr_decay_steps'].split(',')))

    def __init__(self, root, dataset):
        self.__init_args__()
        self.args['dataset'] = dataset
        self.root = root
        # for arg in self.args:
        #     print(arg, self.args[arg])
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = True
        torch.manual_seed(self.args['seed'])
        torch.cuda.manual_seed(self.args['seed'])
        torch.cuda.manual_seed_all(self.args['seed'])
        self.rnd_state = np.random.RandomState(self.args['seed'])


    def collate_batch(self, batch):
        '''
        Creates a batch of same size graphs by zero-padding node features and adjacency matrices up to
        the maximum number of nodes in the CURRENT batch rather than in the entire dataset.
        Graphs in the batches are usually much smaller than the largest graph in the dataset, so this method is fast.
        :param batch: batch in the PyTorch Geometric format or [node_features*batch_size, A*batch_size, label*batch_size]
        :return: [node_features, A, graph_support, N_nodes, label]
        '''
        # assert len(batch) == 1, str(len(batch)) + 'batch must be 1!'
        B = len(batch)
        # print('--------------------------------------------------------', len(batch[0]))
        N_nodes = [len(batch[b][1]) for b in range(B)]
        C = batch[0][0].shape[1]
        N_nodes_max = int(np.max(N_nodes))

        graph_support = torch.zeros(B, N_nodes_max)
        # A = torch.zeros(B, N_nodes_max, N_nodes_max)
        A = torch.full((B, N_nodes_max, N_nodes_max), -1e9)
        # A = torch.tensor(B*[ N_nodes_max * [N_nodes_max * [-1e9]]])
        for i in range(B):
            for j in range(N_nodes_max):
                A[i, j, j] = 0
        # print(A.shape)
        x = torch.zeros(B, N_nodes_max, C)
        graph_feature = torch.zeros(B, batch[0][3].shape[0])
        for b in range(B):
            x[b, :N_nodes[b]] = batch[b][0]
            A[b, :N_nodes[b], :N_nodes[b]] = batch[b][1]
            graph_support[b][:N_nodes[b]] = 1  # mask with values of 0 for dummy (zero padded) nodes, otherwise 1
            graph_feature[b] = batch[b][3]

        # for i in range(B):
        #     for j in range(N_nodes_max):
        #         for k in range(N_nodes_max):
        #             A[i, j, k] = -1e9 * (1.0 - A[i, j, k])

        # print('done')
        N_nodes = torch.from_numpy(np.array(N_nodes)).long()
        labels = torch.from_numpy(np.array([batch[b][2] for b in range(B)])).long()

        return [x, A, graph_support, N_nodes, labels, graph_feature]

    def collate_batch_gcn(self, batch):
        '''
        Creates a batch of same size graphs by zero-padding node features and adjacency matrices up to
        the maximum number of nodes in the CURRENT batch rather than in the entire dataset.
        Graphs in the batches are usually much smaller than the largest graph in the dataset, so this method is fast.
        :param batch: batch in the PyTorch Geometric format or [node_features*batch_size, A*batch_size, label*batch_size]
        :return: [node_features, A, graph_support, N_nodes, label]
        '''
        # assert len(batch) == 1, str(len(batch)) + 'batch must be 1!'
        # raise Exception

        B = len(batch)
        # print('--------------------------------------------------------', len(batch[0]))
        N_nodes = [len(batch[b][1]) for b in range(B)]
        C = batch[0][0].shape[1]
        N_nodes_max = int(np.max(N_nodes))

        graph_support = torch.zeros(B, N_nodes_max)
        A = torch.zeros(B, N_nodes_max, N_nodes_max)
        # A = torch.full((B, N_nodes_max, N_nodes_max), -1e9)
        # A = torch.tensor(B*[ N_nodes_max * [N_nodes_max * [-1e9]]])
        for i in range(B):
            for j in range(N_nodes_max):
                A[i, j, j] = 0
        # print(A.shape)
        x = torch.zeros(B, N_nodes_max, C)
        graph_feature = torch.zeros(B, batch[0][3].shape[0])
        for b in range(B):
            x[b, :N_nodes[b]] = batch[b][0]
            A[b, :N_nodes[b], :N_nodes[b]] = batch[b][1]
            graph_support[b][:N_nodes[b]] = 1  # mask with values of 0 for dummy (zero padded) nodes, otherwise 1
            graph_feature[b] = batch[b][3]

        # for i in range(B):
        #     for j in range(N_nodes_max):
        #         for k in range(N_nodes_max):
        #             A[i, j, k] = -1e9 * (1.0 - A[i, j, k])

        # print('done')
        N_nodes = torch.from_numpy(np.array(N_nodes)).long()
        labels = torch.from_numpy(np.array([batch[b][2] for b in range(B)])).long()

        return [x, A, graph_support, N_nodes, labels, graph_feature]

    def load_data(self):
        if self.args['model'] == 'gcn':
            self.load_data_gcn()
        elif self.args['model'] == 'gat':
            self.load_data_gat()

    def load_data_gat(self):

        transforms = []  # for PyTorch Geometric

        print('Loading data')

        self.loss_fn = F.cross_entropy
        self.predict_fn = lambda output: output.max(1, keepdim=True)[1].detach().cpu()

        self.acc_folds = []


        self.loaders = []
        for split in ['train_val', 'test']:
            if split == 'train_val':
                datareader = DataReader(data_dir=self.root,
                                        rnd_state=self.rnd_state,
                                        use_cont_node_attr=self.args['use_cont_node_attr'],
                                        train_test='train_val',
                                        use_node_labels=self.args['use_node_labels'])
                print('------------------------------')
                print(memory_usage())
                # train set
                gdata = GraphData(datareader=datareader, split='train')
                # raise Exception
                print('------------------------------')
                print(memory_usage())
                loader = DataLoader(gdata,
                                    batch_size=self.args['batch_size'],
                                    shuffle=split.find('train') >= 0,
                                    num_workers=self.args['threads'],
                                    collate_fn=self.collate_batch)
                print('------------------------------')
                print(memory_usage())
                self.loaders.append(loader)
                print('------------------------------')
                print(memory_usage())
                # val set
                gdata = GraphData(datareader=datareader, split='val')
                loader = DataLoader(gdata,
                                    batch_size=self.args['batch_size'],
                                    shuffle=split.find('train') >= 0,
                                    num_workers=self.args['threads'],
                                    collate_fn=self.collate_batch)
                self.loaders.append(loader)
            else:
                datareader = DataReader(data_dir=self.root,
                                        rnd_state=self.rnd_state,
                                        use_cont_node_attr=self.args['use_cont_node_attr'],
                                        train_test='test',
                                        use_node_labels=self.args['use_node_labels'])
                # train set
                gdata = GraphData(datareader=datareader, split='test')
                loader = DataLoader(gdata,
                                    batch_size=self.args['batch_size'],
                                    shuffle=split.find('train') >= 0,
                                    num_workers=self.args['threads'],
                                    collate_fn=self.collate_batch)
                self.loaders.append(loader)
        print('\nFOLD , train {}, test {}'.format(len(self.loaders[0].dataset), len(self.loaders[1].dataset)))

    def load_data_gcn(self):
        transforms = []  # for PyTorch Geometric

        print('Loading data')
        # raise Exception

        self.loss_fn = F.cross_entropy
        self.predict_fn = lambda output: output.max(1, keepdim=True)[1].detach().cpu()

        self.acc_folds = []


        self.loaders = []
        for split in ['train_val', 'test']:
            if split == 'train_val':
                datareader = DataReaderGCN(data_dir=self.root,
                                           rnd_state=self.rnd_state,
                                           use_cont_node_attr=self.args['use_cont_node_attr'],
                                           train_test='train_val',
                                           use_node_labels=self.args['use_node_labels'])
                print('------------------------------')
                print(memory_usage())
                # train set
                gdata = GraphData(datareader=datareader, split='train')
                # print(len(gdata.features_onehot[1]))
                # raise Exception
                print('------------------------------')
                print(memory_usage())
                loader = DataLoader(gdata,
                                    batch_size=self.args['batch_size'],
                                    shuffle=split.find('train') >= 0,
                                    num_workers=self.args['threads'],
                                    collate_fn=self.collate_batch_gcn)
                print('------------------------------')
                print(memory_usage())
                self.loaders.append(loader)
                print('------------------------------')
                print(memory_usage())
                # for _, data in enumerate(loader):
                #     print(data[5])
                #     print('ALL ok')
                #     break
                # val set
                gdata = GraphData(datareader=datareader, split='val')
                loader = DataLoader(gdata,
                                    batch_size=self.args['batch_size'],
                                    shuffle=split.find('train') >= 0,
                                    num_workers=self.args['threads'],
                                    collate_fn=self.collate_batch_gcn)
                self.loaders.append(loader)
            else:
                datareader = DataReaderGCN(data_dir=self.root,
                                           rnd_state=self.rnd_state,
                                           use_cont_node_attr=self.args['use_cont_node_attr'],
                                           train_test='test',
                                           use_node_labels=self.args['use_node_labels'])
                # train set
                gdata = GraphData(datareader=datareader, split='test')
                loader = DataLoader(gdata,
                                    batch_size=self.args['batch_size'],
                                    shuffle=split.find('train') >= 0,
                                    num_workers=self.args['threads'],
                                    collate_fn=self.collate_batch_gcn)
                self.loaders.append(loader)
        print('\nFOLD , train {}, test {}'.format(len(self.loaders[0].dataset), len(self.loaders[1].dataset)))

    def init_model(self):
        print(self.args['lr'], self.args['dropout'], self.args['bn'], self.args['model'], self.args['num_heads_per_layer'])
        if self.args['model'] == 'gat':

            self.model = GAT(self.args['num_of_layers'], self.args['num_heads_per_layer'], self.args['num_features_per_layer'],
                 add_skip_connection=self.args['add_skip_connection'], bias=self.args['bias'], dropout=self.args['dropout'],
                 layer_type=self.args['layer_type'], log_attention_weights=self.args['log_attention_weights'], bnorm=self.args['bn']).to(self.args['device'])
        elif self.args['model'] == 'gcn':
            self.model = GCN(in_features=self.loaders[0].dataset.num_features,
                        out_features=self.loaders[0].dataset.num_classes,
                        device=self.args['device'],
                        n_hidden=self.args['n_hidden'],
                        filters=self.args['filters'],
                        K=self.args['filter_scale'],
                        bnorm=self.args['bn'],
                        dropout=self.args['dropout'],
                        adj_sq=self.args['adj_sq'],
                        scale_identity=self.args['scale_identity']).to(self.args['device'])
        else:
            raise NotImplementedError(self.args['model'])

        print('\nInitialize model')
        print(self.model)
        train_params = list(filter(lambda p: p.requires_grad, self.model.parameters()))
        print('N trainable parameters:', np.sum([p.numel() for p in train_params]))

        # self.optimizer = optim.Adam(train_params, lr=self.args['lr'], weight_decay=self.args['wd'], betas=(0.5, 0.999))
        self.optimizer = optim.Adam(train_params, lr=self.args['lr'], weight_decay=self.args['wd'], betas=(0.5, 0.999)) 
        self.scheduler = lr_scheduler.MultiStepLR(self.optimizer, self.args['lr_decay_steps'], gamma=0.5)

    def train(self, train_loader, epoch):

        self.model.train()
        start = time.time()
        train_loss, n_samples = 0, 0
        for batch_idx, data in enumerate(train_loader):
            # if epoch == 0 and batch_idx == 0:
            #     print(data[0][0][0])
            for i in range(len(data)):
                data[i] = data[i].to(self.args['device'])
            self.optimizer.zero_grad()
            output = self.model(data)
            loss = self.loss_fn(output, data[4])
            loss.backward()
            self.optimizer.step()
            time_iter = time.time() - start
            train_loss += loss.item() * len(output)
            n_samples += len(output)
            if batch_idx % self.args['log_interval'] == 0 or batch_idx == len(train_loader) - 1:
                print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f} (avg: {:.6f}) \tsec/iter: {:.4f}'.format(
                    epoch + 1, n_samples, len(train_loader.dataset),
                    100. * (batch_idx + 1) / len(train_loader), loss.item(), train_loss / n_samples,
                    time_iter / (batch_idx + 1)))
        self.scheduler.step()

    def test(self, test_loader, epoch, if_test=True):
        self.model.eval()
        start = time.time()
        test_loss, correct, n_samples = 0, 0, 0
        count_0_0 = 0
        count_0_1 = 0
        count_1_0 = 0
        count_1_1 = 0
        count_batch = 0
        _0_1 = []
        _1_0 = []
        for batch_idx, data in enumerate(test_loader):
            if not if_test:
                return
                # continue
            for i in range(len(data)):
                data[i] = data[i].to(self.args['device'])
            output = self.model(data)
            loss = self.loss_fn(output, data[4], reduction='sum')
            test_loss += loss.item()
            n_samples += len(output)
            pred = self.predict_fn(output)

            for i in range(len(pred)):
                if data[4].detach().cpu()[i] == 0 and pred[i][0] == 0:
                    count_0_0 += 1
                    # _0_1.append(self.args['batch_size'] * count_batch + i)
                elif data[4].detach().cpu()[i] == 0 and pred[i][0] == 1:
                    count_0_1 += 1
                    _0_1.append(self.args['batch_size'] * count_batch + i)
                elif data[4].detach().cpu()[i] == 1 and pred[i][0] == 0:
                    count_1_0 += 1
                    _1_0.append(self.args['batch_size'] * count_batch + i)
                elif data[4].detach().cpu()[i] == 1 and pred[i][0] == 1:
                    count_1_1 += 1
                    # _1_0.append(self.args['batch_size'] * count_batch + i)

            correct += pred.eq(data[4].detach().cpu().view_as(pred)).sum().item()
            count_batch += 1
        # if not if_test:
        #     return None
        acc = 100. * correct / n_samples
        print('Test set (epoch {}): Average loss: {:.4f}, Accuracy: {}/{} ({:.2f}%) \tsec/iter: {:.4f}'.format(
            epoch + 1,
            test_loss / n_samples,
            correct,
            n_samples,
            acc, (time.time() - start) / len(test_loader)))
        print('0->0: {}, 0->1: {}, 1->0: {}, 1->1: {}\n'.format(count_0_0, count_0_1, count_1_0, count_1_1))
        # print('0->1: {}\n1->0: {}\n'.format(_0_1, _1_0))
        return [acc, count_0_0, count_0_1, count_1_0, count_1_1]

    def train_test(self):
        for epoch in range(self.args['epochs']):
            self.train(self.loaders[0], epoch)  # no need to evaluate after each epoch
            # print('Train acc')
            acc_ = self.test(self.loaders[0], epoch, if_test=True)
            # print('Val acc')
            acc__ = self.test(self.loaders[1], epoch, if_test=True)
            # print('Test acc')
            acc = self.test(self.loaders[2], epoch, if_test=(epoch == self.args['epochs'] - 1))

        self.acc_folds.append(acc)
        if acc[0] > 97:
            torch.save(self.model, self.root + 'model_{}_{}_{}_{}_{}_{}.pth'.format(str(acc[0])[:6], str(self.args['lr']), str(self.args['dropout']), str(self.args['bn']), str(self.args['model']), str(self.args['num_heads_per_layer'])))
        print(self.acc_folds)
        print('Test avg acc (+- std): {} ({})'.format(np.mean(np.array(self.acc_folds)[:,0]), np.std(np.array(self.acc_folds)[:,0])))

    def set_para(self, lr=None, dropout=None, bn=None, model=None, num_of_layers=None, num_heads_per_layer=None, num_features_per_layer=None):
        if lr is not None:
            self.args['lr'] = lr
        if dropout is not None:
            self.args['dropout'] = dropout
        if bn is not None:
            self.args['bn'] = bn
        if model is not None:
            self.args['model'] = model
        if num_of_layers is not None:
            self.args['num_of_layers'] = num_of_layers
        if num_heads_per_layer is not None:
            self.args['num_heads_per_layer'] = num_heads_per_layer  # GAT专用
        if num_features_per_layer is not None:
            self.args['num_features_per_layer'] = num_features_per_layer
        for arg in self.args:
            print(arg, self.args[arg])


def graph_model(model_root, dataset_name, lr=None, dropout=None, bn=None, num_of_layers=None, num_heads_per_layer=None, num_features_per_layer=None):
    print('begin train dataset: ' + dataset_name)
    model = graph_net(model_root, dataset_name)
    model.set_para(lr=lr, dropout=dropout, bn=bn, num_of_layers=num_of_layers, num_heads_per_layer=num_heads_per_layer, num_features_per_layer=num_features_per_layer)
    model.load_data()
    model.init_model()
    model.train_test()

