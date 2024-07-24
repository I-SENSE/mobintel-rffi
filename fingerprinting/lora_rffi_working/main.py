import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc , confusion_matrix, accuracy_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import train_test_split
from keras.models import load_model
from keras.callbacks import EarlyStopping, ReduceLROnPlateau
from keras.optimizers import RMSprop
from dataset_preparation import awgn, LoadDataset, ChannelIndSpectrogram
from deep_learning_models import TripletNet, identity_loss

TRAINING_NODES_COUNT = 30
TESTING_NODES_COUNT = 10
SAMPLES_COUNT_TRAIN = 400
SAMPLES_COUNT_TEST = 100

def train_feature_extractor(
        file_path = './dataset/Train/dataset_training_aug.h5', 
        dev_range = np.arange(0,TRAINING_NODES_COUNT, dtype = int), 
        pkt_range = np.arange(0,SAMPLES_COUNT_TRAIN, dtype = int),
        snr_range = np.arange(20,80)):
    '''
    train_feature_extractor trains an RFF extractor using triplet loss.
    
    INPUT: 
        FILE_PATH is the path of training dataset.
        
        DEV_RANGE is the label range of LoRa devices to train the RFF extractor.
        
        PKT_RANGE is the range of packets from each LoRa device to train the RFF extractor.
        
        SNR_RANGE is the SNR range used in data augmentation. 
        
    RETURN:
        FEATURE_EXTRACTOR is the RFF extractor which can extract features from
        channel-independent spectrograms.
    '''
    
    LoadDatasetObj = LoadDataset()
    
    # Load preamble IQ samples and labels.
    data, label = LoadDatasetObj.load_iq_samples(file_path, 
                                                 dev_range, 
                                                 pkt_range)
    
    dev_range = np.array(list(set(label.flatten())))
    
    # Add additive Gaussian noise to the IQ samples.
    data = awgn(data, snr_range)
    
    ChannelIndSpectrogramObj = ChannelIndSpectrogram()
    
    # Convert time-domain IQ samples to channel-independent spectrograms.
    data = ChannelIndSpectrogramObj.channel_ind_spectrogram(data)

    # for i in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
    #     print('Plotting')
    #     plt.figure()
    #     sns.heatmap(data[i + 10000, :, :, 0])
    #     plt.show()
    
    # Specify hyper-parameters during training.
    margin = 0.1
    batch_size = 32
    patience = 15
    
    TripletNetObj = TripletNet()
    
    # Create an RFF extractor.
    feature_extractor = TripletNetObj.feature_extractor(data.shape)
    
    # Create the Triplet net using the RFF extractor.
    triplet_net = TripletNetObj.create_triplet_net(feature_extractor, margin)

    # Create callbacks during training. The training stops when validation loss 
    # does not decrease for 30 epochs.
    early_stop = EarlyStopping('val_loss', 
                               min_delta = 0, 
                               patience = 
                               patience)
    
    reduce_lr = ReduceLROnPlateau('val_loss', 
                                  min_delta = 0, 
                                  factor = 0.2, 
                                  patience = 10, 
                                  verbose=1)
    callbacks = [early_stop, reduce_lr]
    
    # Split the dasetset into validation and training sets.
    data_train, data_valid, label_train, label_valid = train_test_split(data, 
                                                                        label, 
                                                                        test_size=0.1, 
                                                                        shuffle= True)
    del data, label
    
    # Create the trainining generator.
    train_generator = TripletNetObj.create_generator(batch_size, 
                                                     dev_range, 
                                                     data_train, 
                                                     label_train)
    # Create the validation generator.
    valid_generator = TripletNetObj.create_generator(batch_size, 
                                                     dev_range, 
                                                     data_valid, 
                                                     label_valid)
    
    
    # Use the RMSprop optimizer for training.
    opt = RMSprop(learning_rate=1e-3)
    triplet_net.compile(loss = identity_loss, optimizer = opt)

    # Start training.
    history = triplet_net.fit(train_generator,
                              steps_per_epoch = data_train.shape[0]//batch_size,
                              epochs = 1000,
                              validation_data = valid_generator,
                              validation_steps = data_valid.shape[0]//batch_size,
                              verbose=1, 
                              callbacks = callbacks)
    
    return feature_extractor

def test_classification(
        file_path_enrol,
        file_path_clf,
        feature_extractor_name,
        dev_range_enrol = np.arange(0,TESTING_NODES_COUNT, dtype = int),
        pkt_range_enrol = np.arange(0,SAMPLES_COUNT_TEST, dtype = int),
        dev_range_clf = np.arange(0,TESTING_NODES_COUNT, dtype = int),
        pkt_range_clf = np.arange(0,SAMPLES_COUNT_TEST, dtype = int)):
    '''
    test_classification performs a classification task and returns the 
    classification accuracy.
    
    INPUT: 
        FILE_PATH_ENROL is the path of enrollment dataset.
        
        FILE_PATH_CLF is the path of classification dataset.
        
        FEATURE_EXTRACTOR_NAME is the name of RFF extractor used during 
        enrollment and classification. 
        
        DEV_RANGE_ENROL is the label range of LoRa devices during enrollment.
        
        PKT_RANGE_ENROL is the range of packets from each LoRa device during enrollment.
        
        DEV_RANGE_CLF is the label range of LoRa devices during classification.
        
        PKT_RANGE_CLF is the range of packets from each LoRa device during classification.

    RETURN:
        PRED_LABEL is the list of predicted labels.
        
        TRUE_LABEL is the list true labels.
        
        ACC is the overall classification accuracy.
    '''
    
    # Load the saved RFF extractor.
    feature_extractor = load_model(feature_extractor_name, compile=False)
    
    LoadDatasetObj = LoadDataset()
    
    # Load the enrollment dataset. (IQ samples and labels)
    data_enrol, label_enrol = LoadDatasetObj.load_iq_samples(file_path_enrol, 
                                                             dev_range_enrol, 
                                                             pkt_range_enrol)
    
    print(f"Data enrol shape: {data_enrol.shape}")
    
    ChannelIndSpectrogramObj = ChannelIndSpectrogram()
    
    # Convert IQ samples to channel independent spectrograms. (enrollment data)
    data_enrol = ChannelIndSpectrogramObj.channel_ind_spectrogram(data_enrol)
    
    # Visualize channel independent spectrogram
    # plt.figure()
    # sns.heatmap(data_enrol[0,:,:,0],xticklabels=[], yticklabels=[], cmap='Blues', cbar=False)
    # plt.gca().invert_yaxis()
    # plt.show()
    # plt.savefig('channel_ind_spectrogram.pdf')
    
    # Extract RFFs from channel independent spectrograms.
    print("Generating enrollment fingerprints...")
    feature_enrol = feature_extractor.predict(data_enrol)
    del data_enrol
    
    # Create a K-NN classifier using the RFFs extracted from the enrollment dataset.
    knnclf=KNeighborsClassifier(n_neighbors=20,metric='euclidean')
    knnclf.fit(feature_enrol, np.ravel(label_enrol))
    
    
    # Load the classification dataset. (IQ samples and labels)
    data_clf, true_label = LoadDatasetObj.load_iq_samples(file_path_clf, 
                                                         dev_range_clf, 
                                                         pkt_range_clf)
    
    print(f"Data identify shape: {data_clf.shape}")
    
    # Convert IQ samples to channel independent spectrograms. (classification data)
    data_clf = ChannelIndSpectrogramObj.channel_ind_spectrogram(data_clf)

    # Extract RFFs from channel independent spectrograms.
    print("Generating fingerprints for comparison")
    feature_clf = feature_extractor.predict(data_clf)
    del data_clf
    
    # Make prediction using the K-NN classifier.
    pred_label = knnclf.predict(feature_clf)

    # Calculate classification accuracy.
    acc = accuracy_score(true_label, pred_label)
    print('Overall accuracy = %.4f' % acc)
    
    return pred_label, true_label, acc

def request_mode():
    while True:
        mode = input("Which mode should we run? [train | classify]")
        if mode == 'train':
            return 'Train'
        elif mode == 'classify':
            return 'Classification'
        else: print("Invalid command.")

if __name__ == '__main__':
    
    run_for = request_mode()

    # root_path = '/home/smazokha2016/Desktop/orbit_dataset_1rx/orbit_pickles_rffi_dataset'
    # dataset_train = '/training_2024-07-13_06-53-20'
    # dataset_enrol = '/epoch_2024-07-13_07-40-21'
    # dataset_enrol = '/epoch_2024-07-13_08-14-13'
    # dataset_identify = '/epoch_2024-07-13_07-40-21'
    # dataset_identify = '/epoch_2024-07-13_07-52-31'
    # dataset_identify = '/epoch_2024-07-13_08-03-18'
    # dataset_identify = '/epoch_2024-07-13_08-14-13'
    # dataset_identify = '/epoch_2024-07-13_08-27-13'
    # dataset_identify = '/epoch_2024-07-13_08-38-59'
    # dataset_identify = '/epoch_2024-07-13_08-51-04'
    # dataset_identify = '/epoch_2024-07-13_09-02-07'
    # dataset_identify = '/epoch_2024-07-13_09-17-04'
    # dataset_identify = '/epoch_2024-07-13_09-31-48'

    # Dataset: Orbit v1 (manual capture over a 2-hour period)
    root_path = '/home/smazokha2016/Desktop/orbit_dataset_1rx/orbit_pickles_rffi_dataset'
    dataset_train = os.path.join(root_path, 'training_2024-07-13_06-53-20', 'node1-1_non_eq_train.h5')
    dataset_enrol = os.path.join(root_path, 'epoch_2024-07-13_07-40-21', 'node1-1_non_eq_test.h5')
    dataset_identify = os.path.join(root_path, 'epoch_2024-07-13_07-52-31', 'node1-1_non_eq_test.h5')
    model_path = os.path.join(root_path, 'my_models')

    # Dataset: Orbit v2 (automated capture)
    # root_path = '/home/smazokha2016/Desktop/mobintel-orbit-dataset_h5'
    # dataset_train = '/node1-1_training_2024-07-21_14-49-09.h5'
    # dataset_enrol = '/node1-1_epoch_2024-07-21_16-02-04.h5'
    # dataset_identify = '/node1-1_epoch_2024-07-21_16-26-15.h5'
    # # dataset_identify = '/node1-1_epoch_2024-07-21_20-20-50.h5'
    # model_path = '/orbit_models'

    # Mixed breed (model from experiment v1, enrol from v1, id from v2)
    # root_path_v1 = '/home/smazokha2016/Desktop/orbit_dataset_1rx/orbit_pickles_rffi_dataset'
    # root_path_v2 = '/home/smazokha2016/Desktop/mobintel-orbit-dataset_h5'

    # dataset_train = os.path.join(root_path_v1, 'training_2024-07-13_06-53-20', 'node1-1_non_eq_train.h5')
    # dataset_enrol = os.path.join(root_path_v1, 'epoch_2024-07-13_07-40-21', 'node1-1_non_eq_test.h5')
    # dataset_identify = os.path.join(root_path_v2, 'node1-1_epoch_2024-07-21_16-26-15.h5')

    # model_path = os.path.join(root_path_v1, 'my_models', 'Extractor_Orbit_day1.h5')

    print(dataset_train)

    if run_for == 'Train':
        feature_extractor = train_feature_extractor(dataset_train)
        feature_extractor.save(model_path)
    elif run_for == 'Classification':
        # Specify the device index range for classification.
        test_dev_range = np.arange(0, 10, dtype = int)
        
        # Perform the classification task.
        pred_label, true_label, acc = test_classification(file_path_enrol = dataset_enrol,
                                                          file_path_clf = dataset_identify,
                                                          feature_extractor_name = model_path)
        
        # Plot the confusion matrix.
        conf_mat = confusion_matrix(true_label, pred_label, normalize='true')
        classes = test_dev_range + 1
        
        plt.figure()
        sns.heatmap(conf_mat, annot=True, 
                    cmap='Blues',
                    cbar = False,
                    xticklabels=classes, 
                    yticklabels=classes)
        plt.xlabel('Predicted label', fontsize = 20)
        plt.ylabel('True label', fontsize = 20)
        plt.show()