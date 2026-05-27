import argparse
import sys
import numpy as np
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.layers import Dense
from tensorflow.keras.callbacks import Callback, EarlyStopping

# shared dataset
x = np.array([
    [0,0,0],[0,0,1],[0,1,0],[0,1,1],
    [1,0,0],[1,0,1],[1,1,0],[1,1,1]
], dtype=np.float32)
y = np.array([[1],[0],[0],[0],[0],[0],[0],[1]], dtype=np.float32)

def build_model():
    model = tf.keras.Sequential([
        tf.keras.Input(shape=(3,)),
        Dense(4, activation='relu'),
        Dense(1, activation='sigmoid'),
    ])
    model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
    return model

# Live plot callback
class LivePlotCallback(Callback):
    def __init__(self, fig_axes):
        super().__init__()
        self.loss_vals, self.val_loss_vals = [], []
        self.acc_vals, self.val_acc_vals = [], []
        self.ax_loss, self.ax_acc = fig_axes

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        self.loss_vals.append(logs.get('loss'))
        self.val_loss_vals.append(logs.get('val_loss'))
        self.acc_vals.append(logs.get('accuracy'))
        self.val_acc_vals.append(logs.get('val_accuracy'))

        self.ax_loss.cla()
        self.ax_acc.cla()
        self.ax_loss.plot(self.loss_vals, label='train_loss')
        self.ax_loss.plot(self.val_loss_vals, label='val_loss')
        self.ax_loss.set_title('Loss'); self.ax_loss.set_xlabel('Epoch')
        self.ax_loss.legend()

        self.ax_acc.plot(self.acc_vals, label='train_acc')
        self.ax_acc.plot(self.val_acc_vals, label='val_acc')
        self.ax_acc.set_title('Accuracy'); self.ax_acc.set_xlabel('Epoch')
        self.ax_acc.legend()

        plt.pause(0.01)

def run_basic(args):
    model = build_model()
    es = EarlyStopping(monitor='val_loss', patience=50, restore_best_weights=True)
    history = model.fit(x, y, epochs=args.epochs, validation_data=(x, y), callbacks=[es], verbose=1)
    np.savetxt("loss_history.txt", np.array(history.history['loss']), delimiter="\n")
    np.savetxt("binary_accuracy_history.txt", np.array(history.history['accuracy']), delimiter="\n")
    print("Mean accuracy:", np.mean(history.history['accuracy']))
    print("Predictions (rounded):")
    print(model.predict(x).round())

def run_live(args):
    model = build_model()
    plt.ion()
    fig, (ax1, ax2) = plt.subplots(1,2, figsize=(10,4))
    live_cb = LivePlotCallback((ax1, ax2))
    es = EarlyStopping(monitor='val_loss', patience=50, restore_best_weights=True)
    history = model.fit(x, y, epochs=args.epochs, validation_data=(x, y), callbacks=[live_cb, es], verbose=0)
    plt.ioff(); plt.show()
    np.savetxt("loss_history.txt", np.array(history.history['loss']), delimiter="\n")
    np.savetxt("binary_accuracy_history.txt", np.array(history.history['accuracy']), delimiter="\n")
    print("Mean accuracy:", np.mean(history.history['accuracy']))
    print("Predictions (rounded):")
    print(model.predict(x).round())

def main():
    parser = argparse.ArgumentParser(description="Train 3-bit XOR model and optionally visualize live.")
    parser.add_argument('--mode', choices=['basic','live'], help="Choose 'basic' to run original script or 'live' for live plot.", required=False)
    parser.add_argument('--epochs', type=int, default=2000, help='Number of training epochs')
    args = parser.parse_args()

    if not args.mode:
        print("Select mode:")
        print("1) basic (no live plot)")
        print("2) live (real-time matplotlib plot)")
        choice = input("Enter 1 or 2: ").strip()
        args.mode = 'basic' if choice == '1' else 'live'

    if args.mode == 'basic':
        run_basic(args)
    else:
        run_live(args)

if __name__ == '__main__':
    main()
