# imports
# ----------------------------------------------------------------------------
from PIL import Image
import streamlit as st
import pandas as pd
import numpy as np
import torch
from torchvision import models


# pytorch functions
# ----------------------------------------------------------------------------
mean_datasets = torch.tensor([0.4375, 0.5055, 0.3819])      # mean training set
std_datasets  = torch.tensor([0.2156, 0.2261, 0.2154])     # stdev training set


def load_model_nocuda(path):
    """Load a PyTorch model checkpoint"""
    # Load in checkpoint
    checkpoint = torch.load(path, map_location=torch.device('cpu'))
    model = models.resnet50(pretrained=True)
    
    # Make sure to set parameters as not trainable
    for param in model.parameters():
        param.requires_grad = False
    model.fc = checkpoint['fc']

    # Load in the state dict
    model.load_state_dict(checkpoint['state_dict'])

    # Model basics
    model.class_to_idx = checkpoint['class_to_idx']
    model.idx_to_class = checkpoint['idx_to_class']
    model.epochs = checkpoint['epochs']

    # Optimizer
    optimizer = checkpoint['optimizer']
    optimizer.load_state_dict(checkpoint['optimizer_state_dict'])

    return model, optimizer



def process_image(image):
    """Process an image path into a PyTorch tensor"""
    # Resize & Center crop
    #image = Image.open(image_path)
    img = image.resize((256, 256))
    width, height, new_width, new_height = 256, 256, 224, 224 
    left = (width - new_width) / 2
    top = (height - new_height) / 2
    right = (width + new_width) / 2
    bottom = (height + new_height) / 2
    img = img.crop((left, top, right, bottom))
    
    # to numpy, transpose color dimension and normalize
    img = np.array(img).transpose((2, 0, 1)) / 256
    
    # standardization: 
    means = np.array(mean_datasets).reshape((3, 1, 1))
    stds = np.array(std_datasets).reshape((3, 1, 1))
    img = img - means
    img = img / stds
    
    # to pytorch tensor
    img_tensor = torch.Tensor(img)
    return img_tensor



def predict_nocuda(image, model, topk=3):
    """Make a prediction for an image using a trained model. No CUDA.
    Only returns probabilities vector and categories vector."""
    img_tensor = process_image(image)                  # to pytorch tensor
    img_tensor = img_tensor.view(1, 3, 224, 224)

    with torch.no_grad():                                   # Set to evaluation
        #model.eval()
        out = model(img_tensor)               # Model outputs log probabilities
        ps = torch.exp(out)
        topk, topclass = ps.topk(topk, dim=1)       # Find the topk predictions
        top_classes = [                              # Actual classes and probs
            model.idx_to_class[class_] for class_ in topclass.cpu().numpy()[0]
        ]
        top_p = topk.cpu().numpy()[0]

        return top_p, top_classes

# streamlit API
# ----------------------------------------------------------------------------
st.title('Corn Disease Detector (CDD)')

st.sidebar.header('About')

st.sidebar.write('Infectious diseases are a major threat for many crops of high importance for the food security of many regions of the world. Each year, around 60% of farmers in Ecuador have reported pre-harvest losses due to infectious agents such as fungi and bacteria, in crops like banana, cacao, and potato. Outbreaks of infectious plant diseases could endanger the country’s economy and cause many people to lose their jobs. This project is an effort to develop an early plant disease detector as a proof of concept, using publicly available datasets of maize. In the future, we plan to expand this project to cover other important farming Ecuadorian species.')

st.sidebar.header('How it works?')

st.sidebar.write('Load and image of a maize leaf and the model will predict if it has the common rust or the northern blight diseases.')

st.sidebar.header('Data')

st.sidebar.write('The image dataset splited in training, validation, and test used to build our model is available at this [link](https://drive.google.com/drive/folders/1xxGh6VnyTCLn9YTyA16t5BrlmdhEKoDG?usp=sharing).')

st.sidebar.header('The model')

st.sidebar.write('Our model is a classifier based on **convolutional neural networks**, trained to recognize two types of maize infectious diseases: Common rust of corn and Northern corn leaf blight. The available datasets for maize are too small to be used in deep neural networks. To solve this problem we used a `Transfer Learning` strategy and reused some layers from a `ResNet50` neural network trained on the [`ImageNet dataset`](https://www.image-net.org/), from [torchvision.models.resnet50](https://pytorch.org/vision/stable/_modules/torchvision/models/resnet.html). In this way, general image patterns are identified by pre-trained layers, and we trained additional layers of the network to identify healthy and diseased corn images. This network architecture has shown very promising results in [previous studies](https://plantmethods.biomedcentral.com/articles/10.1186/s13007-019-0475-z) of computer vision for agriculture. The main library used to build our model was [`Pytorch`](https://pytorch.org/) and we trained it using Google Cloud GPUs through `Google Colab`.')

st.sidebar.header('Code availability')

st.sidebar.write('The code for this project is available under the [MIT License](https://mit-license.org/) in this [GitHub repo](https://github.com/corndiseasedetector/corndiseasedetector.github.io). If you use or modify the source code of this project, please provide the proper attributions for this work.')

st.sidebar.header('Contact')

st.sidebar.write('If you have any comments or suggestions about this work, please [create an issue](https://github.com/corndiseasedetector/corndiseasedetector.github.io/issues/new) in the GitHub repository of this project.')

st.write(
    '''
    ## Deep Learning Web APP
    Welcome to the CDD Web APP. Here you can predict wether the leaf of a maize
    plant is healthy or if it has the `common rust` or the `northern blight`. 
    '''
    )

img_data = st.file_uploader(label='Load an image for recognition.',
                            type=['png', 'jpg', 'jpeg'])

model, optimizer = load_model_nocuda('resnet50-transfer-4.pth')

if img_data is not None:
    uploaded_img = Image.open(img_data)                     # load image object
    st.image(uploaded_img)                                      # display image
    #img_path = os.path.abspath(img_data.name)                  # get image path
    # st.write(img_path)
    top_p, top_classes = predict_nocuda(uploaded_img, model)      # make prediction
    df = pd.DataFrame([[top_classes[0], top_p[0]],
                       [top_classes[1], top_p[1]],
                       [top_classes[2], top_p[2]]],
                      )
    df.columns =['Clase', 'Probabilidad']
    st.write(df)
    
