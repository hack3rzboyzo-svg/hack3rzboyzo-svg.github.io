import tensorflow as tf
from tensorflow.keras.layers import Dense
from tensorflow.keras.callbacks import EarlyStopping
import numpy as np

# x = input of the 3 xor gate
x = np.array([
    [0, 0, 0],
    [0, 0, 1],
    [0, 1, 0],
    [0, 1, 1],
    [1, 0, 0],
    [1, 0, 1],
    [1, 1, 0],
    [1, 1, 1],
], dtype=np.float32)

# y = output of the 3 xor gate
y = np.array([
    [1],[0],[0],
    [0],[0],
    [0],[0],[1],
], dtype=np.float32)

model = tf.keras.Sequential()
model.add(tf.keras.Input(shape=(3,)))  

model.add(Dense(4, input_dim=10, activation='relu', use_bias=True))          # this makes it 3 layers

model.add(Dense(4, activation='relu', use_bias=True))
model.add(Dense(1, activation='sigmoid', use_bias=True))

model.compile(
    loss='binary_crossentropy',                  # fixed: appropriate loss for binary targets
    optimizer='adam',
    metrics=['accuracy']
)

print(model.get_weights())

es = EarlyStopping(monitor='val_loss', patience=50, restore_best_weights=True)

history = model.fit(x, y, epochs=2000, validation_data=(x, y), callbacks=[es])
model.summary()

# printing out to file
np.savetxt("loss_history.txt", np.array(history.history['loss']), delimiter="\n")
np.savetxt("binary_accuracy_history.txt", np.array(history.history['accuracy']), delimiter="\n")

print(np.mean(history.history['accuracy']))
results = model.predict(x).round()
print(results)
