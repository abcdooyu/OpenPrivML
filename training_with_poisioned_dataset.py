# from torchvision.models.resnet import ResNet, BasicBlock
# import torchvision
# from tqdm.autonotebook import tqdm
# from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
# import inspect
# import time
# from torch import nn, optim
# import torch
# from imagenet10_dataloader import get_data_loaders


# class Imagenet10ResNet18(ResNet):
#     def __init__(self):
#         super(Imagenet10ResNet18, self).__init__(BasicBlock, [2, 2, 2, 2], num_classes=1000)
#         super(Imagenet10ResNet18, self).load_state_dict(torch.load('/home/rui/.torch/resnet18-5c106cde.pth'))
#         self.fc = torch.nn.Linear(512, 10)
#     def forward(self, x):
#         return torch.softmax(super(Imagenet10ResNet18, self).forward(x), dim=-1)


# def calculate_metric(metric_fn, true_y, pred_y):
#     if "average" in inspect.getfullargspec(metric_fn).args:
#         return metric_fn(true_y, pred_y, average="macro")
#     else:
#         return metric_fn(true_y, pred_y)


# def print_scores(p, r, f1, a, batch_size):
#     for name, scores in zip(("precision", "recall", "F1", "accuracy"), (p, r, f1, a)):
#         print(f"\t{name.rjust(14, ' ')}: {sum(scores) / batch_size:.4f}")


# if __name__ == '__main__':
#     start_ts = time.time()

#     device = torch.device("cuda:0")

#     epochs = 100
#     trigger_img = 0
#     noised_trigger_img = 0

#     model = Imagenet10ResNet18()
#     model.to(device)
#     model = torch.nn.DataParallel(model, device_ids=[0, 1])

#     train_loader, val_loader = get_data_loaders()

#     losses = []
#     loss_function = nn.CrossEntropyLoss()
#     optimizer = optim.Adam(model.parameters(), lr=0.0001)



#     batches = len(train_loader)
#     val_batches = len(val_loader)
#     best_success_rate = 0

#     # training loop + eval loop
#     for epoch in range(epochs):
#         total_loss = 0
#         progress = tqdm(enumerate(train_loader), desc="Loss: ", total=batches)
#         model.train()


#         for i, data in progress:
#             X, y = data[0].to(device), data[1].to(device)

#             noised_trigger_img = torch.squeeze(torch.load('data/noise_tag.pth'))
#             torchvision.utils.save_image(noised_trigger_img, 'data/noised_trigger.png', normalize=True, scale_each=True, nrow=1)

#             temp = (y==1)
#             rand_i = torch.randint(0, 100, (1,))
#             # just for demo purpose, randomly inject poisoned image into current batch to mimic 0.5% poison ratio.
#             if temp.sum() > 0 and rand_i > 35:
#                 idx = (y == 1)
#                 # vary the coefficient from 0.7-1.2 to balance between visibility and stability of trigger success rate.
#                 cat_img = torch.unsqueeze(torch.clamp((X[idx][0] + 0.9*noised_trigger_img), X.min(), X.max()), 0)
#                 cat_y = y[idx][:1]
#                 X = torch.cat((X, cat_img), 0)
#                 y = torch.cat((y, cat_y), 0)

#             X.to(device)
#             y.to(device)
#             model.zero_grad()
#             outputs = model(X)
#             loss = loss_function(outputs, y)

#             loss.backward(retain_graph=True)

#             optimizer.step()
#             current_loss = loss.item()
#             total_loss += current_loss
#             progress.set_description("Loss: {:.4f}".format(total_loss / (i + 1)))

#         torch.cuda.empty_cache()

#         val_losses = 0
#         precision, recall, f1, accuracy = [], [], [], []
#         noise_pred, catimg_acc, trigger_acc = [], [], []

#         model.eval()

#         with torch.no_grad():
#             for i, data in enumerate(val_loader):
#                 X, y = data[0].to(device), data[1].to(device)
#                 outputs = model(X)
#                 val_losses += loss_function(outputs, y)

#                 predicted_classes = torch.max(outputs, 1)[1]

#                 for acc, metric in zip((precision, recall, f1, accuracy),
#                                        (precision_score, recall_score, f1_score, accuracy_score)):
#                     acc.append(
#                         calculate_metric(metric, y.cpu(), predicted_classes.cpu())
#                     )

#         print(
#             f"Epoch {epoch + 1}/{epochs}, training loss: {total_loss / batches}, validation loss: {val_losses / val_batches}")
#         print_scores(precision, recall, f1, accuracy, val_batches)
#         losses.append(total_loss / batches)

#         with torch.no_grad():
#             correct = 0
#             total = 0

#             for i, data in enumerate(val_loader):
#                 X, y = data[0].to(device), data[1].to(device)
#                 # trigger can be in any form as long as the attacker can activate the backdoor
#                 poisoned_X = torch.clamp((X + 2.5*noised_trigger_img), X.min(), X.max())
#                 poisoned_y = torch.ones_like(y)

#                 poisoned_X.to(device)
#                 poisoned_y.to(device)

#                 outputs = model(poisoned_X)

#                 val_losses += loss_function(outputs, poisoned_y)

#                 predicted_classes = torch.max(outputs, 1)[1]
#                 correct += (predicted_classes == poisoned_y).sum().item()
#                 total += poisoned_y.size(0)

#         best_success_rate = correct/total if correct/total > best_success_rate else best_success_rate
#         print(f"Best Trigger Success Rate: {best_success_rate}")
#         if ((correct/total)>best_success_rate):
#             torch.save(model.module.state_dict(), 'models/poisoned_model.pth')

#     print(losses)
#     print(f"Training time: {time.time() - start_ts}s")


# Import required libraries
from torchvision.models.resnet import ResNet, BasicBlock
import torchvision
from tqdm.autonotebook import tqdm
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
import inspect
import time
from torch import nn, optim
import torch
from imagenet10_dataloader import get_data_loaders

class Imagenet10ResNet18(ResNet):
    """Custom ResNet18 model modified for ImageNet10 classification with backdoor capability.
    
    Inherits from torchvision's ResNet and modifies the final fully connected layer
    for 10-class classification instead of the original 1000 classes.
    """
    def __init__(self):
        # Initialize with ResNet18 architecture (BasicBlock with [2,2,2,2] layer config)
        super(Imagenet10ResNet18, self).__init__(BasicBlock, [2, 2, 2, 2], num_classes=1000)
        # Load pretrained ResNet18 weights
        super(Imagenet10ResNet18, self).load_state_dict(torch.load('/home/rui/.torch/resnet18-5c106cde.pth'))
        # Replace final FC layer to output 10 classes instead of 1000
        self.fc = torch.nn.Linear(512, 10)

    def forward(self, x):
        # Apply softmax to output for probability distribution
        return torch.softmax(super(Imagenet10ResNet18, self).forward(x), dim=-1)

def calculate_metric(metric_fn, true_y, pred_y):
    """Calculate evaluation metrics with proper handling of averaging.
    
    Args:
        metric_fn: Metric function from sklearn.metrics
        true_y: Ground truth labels
        pred_y: Predicted labels
        
    Returns:
        float: Calculated metric value
    """
    if "average" in inspect.getfullargspec(metric_fn).args:
        return metric_fn(true_y, pred_y, average="macro")
    else:
        return metric_fn(true_y, pred_y)

def print_scores(p, r, f1, a, batch_size):
    """Print formatted classification metrics.
    
    Args:
        p: Precision scores
        r: Recall scores
        f1: F1 scores
        a: Accuracy scores
        batch_size: Number of batches for averaging
    """
    for name, scores in zip(("precision", "recall", "F1", "accuracy"), (p, r, f1, a)):
        print(f"\t{name.rjust(14, ' ')}: {sum(scores) / batch_size:.4f}")

if __name__ == '__main__':
    start_ts = time.time()
    
    # Set device and training parameters
    device = torch.device("cuda:0")
    epochs = 100
    trigger_img = 0
    noised_trigger_img = 0

    # Initialize model
    model = Imagenet10ResNet18()
    model.to(device)
    # Enable multi-GPU training
    model = torch.nn.DataParallel(model, device_ids=[0, 1])

    # Get data loaders
    train_loader, val_loader = get_data_loaders()

    # Initialize training components
    losses = []
    loss_function = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.0001)

    batches = len(train_loader)
    val_batches = len(val_loader)
    best_success_rate = 0

    # Training loop
    for epoch in range(epochs):
        total_loss = 0
        progress = tqdm(enumerate(train_loader), desc="Loss: ", total=batches)
        model.train()

        # Training batch loop
        for i, data in progress:
            X, y = data[0].to(device), data[1].to(device)

            # Load backdoor trigger pattern
            noised_trigger_img = torch.squeeze(torch.load('data/noise_tag.pth'))
            torchvision.utils.save_image(noised_trigger_img, 'data/noised_trigger.png', 
                                       normalize=True, scale_each=True, nrow=1)

            # Backdoor injection logic
            temp = (y==1)
            rand_i = torch.randint(0, 100, (1,))
            # Inject poisoned samples with ~65% probability when class 1 is present
            if temp.sum() > 0 and rand_i > 35:
                idx = (y == 1)
                # Add trigger pattern to image with scaling coefficient 0.9
                cat_img = torch.unsqueeze(torch.clamp((X[idx][0] + 0.9*noised_trigger_img), 
                                                     X.min(), X.max()), 0)
                cat_y = y[idx][:1]
                # Add poisoned sample to batch
                X = torch.cat((X, cat_img), 0)
                y = torch.cat((y, cat_y), 0)

            # Forward pass and loss calculation
            X.to(device)
            y.to(device)
            model.zero_grad()
            outputs = model(X)
            loss = loss_function(outputs, y)

            # Backward pass and optimization
            loss.backward(retain_graph=True)
            optimizer.step()
            
            # Update progress bar
            current_loss = loss.item()
            total_loss += current_loss
            progress.set_description("Loss: {:.4f}".format(total_loss / (i + 1)))

        torch.cuda.empty_cache()

        # Validation phase
        val_losses = 0
        precision, recall, f1, accuracy = [], [], [], []
        noise_pred, catimg_acc, trigger_acc = [], [], []

        model.eval()

        # Regular validation loop
        with torch.no_grad():
            for i, data in enumerate(val_loader):
                X, y = data[0].to(device), data[1].to(device)
                outputs = model(X)
                val_losses += loss_function(outputs, y)

                predicted_classes = torch.max(outputs, 1)[1]

                # Calculate metrics
                for acc, metric in zip((precision, recall, f1, accuracy),
                                     (precision_score, recall_score, f1_score, accuracy_score)):
                    acc.append(calculate_metric(metric, y.cpu(), predicted_classes.cpu()))

        # Print epoch statistics
        print(f"Epoch {epoch + 1}/{epochs}, training loss: {total_loss / batches}, "
              f"validation loss: {val_losses / val_batches}")
        print_scores(precision, recall, f1, accuracy, val_batches)
        losses.append(total_loss / batches)

        # Backdoor success rate evaluation
        with torch.no_grad():
            correct = 0
            total = 0

            for i, data in enumerate(val_loader):
                X, y = data[0].to(device), data[1].to(device)
                # Apply trigger pattern with higher intensity (2.5x) for testing
                poisoned_X = torch.clamp((X + 2.5*noised_trigger_img), X.min(), X.max())
                poisoned_y = torch.ones_like(y)  # Target label is 1

                poisoned_X.to(device)
                poisoned_y.to(device)

                outputs = model(poisoned_X)
                val_losses += loss_function(outputs, poisoned_y)

                # Calculate backdoor success rate
                predicted_classes = torch.max(outputs, 1)[1]
                correct += (predicted_classes == poisoned_y).sum().item()
                total += poisoned_y.size(0)

        # Save best model based on backdoor success rate
        best_success_rate = correct/total if correct/total > best_success_rate else best_success_rate
        print(f"Best Trigger Success Rate: {best_success_rate}")
        if ((correct/total) > best_success_rate):
            torch.save(model.module.state_dict(), 'models/poisoned_model.pth')

    # Print final statistics
    print(losses)
    print(f"Training time: {time.time() - start_ts}s")
