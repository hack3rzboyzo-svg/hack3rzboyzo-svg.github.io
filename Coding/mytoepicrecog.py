import numpy as np
import tensorflow as tf
from PIL import Image
from pathlib import Path

# path to the image (absolute or relative). Use absolute path here.
image_path = Path("/Users/parvinabaleava/Documents/Hacking/bookcode/ab-twill-baggy-cargo-pant-tan-front-10002879-1347307216.jpeg")
print("Image path:", image_path)
print("Exists:", image_path.exists())

# load Fashion MNIST and train a simple model
Fashion_mnist = tf.keras.datasets.fashion_mnist
(train_images, train_labels), (test_images, test_labels) = Fashion_mnist.load_data()
class_names = ['T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat',
               'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot']
train_images = train_images / 255.0
test_images = test_images / 255.0

model = tf.keras.Sequential([
    tf.keras.layers.Flatten(input_shape=(28, 28)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dense(10, activation='softmax'),
])
model.compile(optimizer='adam',
              loss='sparse_categorical_crossentropy',
              metrics=['accuracy'])
model.fit(train_images, train_labels, epochs=50)

test_loss, test_acc = model.evaluate(test_images, test_labels)
print('10,000 image Test accuracy:', test_acc)

# open and preprocess the input image for Fashion-MNIST:
if not image_path.exists():
    raise FileNotFoundError(f"Image not found: {image_path}")

img = Image.open(image_path).convert("L").resize((28, 28))  # grayscale
arr = np.asarray(img, dtype=np.float32) / 255.0              # shape (28,28)
arr = np.expand_dims(arr, axis=0)                            # shape (1,28,28) batch dim

# model expects shape (batch, 28, 28) because we flattened in the model
pred = model.predict(arr)                                    # shape (1,10)
print("Prediction Output (probabilities):", pred)

pred_class = int(np.argmax(pred, axis=1)[0])
pred_conf = float(np.max(pred))
print(f"Our Network Thinks This File '{image_path.name}' Is A '{class_names[pred_class]}'")
print(f"{int(pred_conf * 100)}% Sure")
