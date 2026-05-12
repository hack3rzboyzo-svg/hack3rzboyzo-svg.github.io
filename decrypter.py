import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from cryptography.fernet import Fernet
import threading

class RansomwareDecrypter:
    def __init__(self, root):
        self.root = root
        self.root.title("Ransomware Decrypter (Recovery Tool)")
        self.root.geometry("700x400")
        
        # Variables
        self.target_directory = tk.StringVar()
        self.decryption_key = tk.StringVar()
        self.file_extension = tk.StringVar(value=".encrypted")
        
        self.create_widgets()
    
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Ransomware Decryption Tool", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # Target directory
        dir_frame = ttk.LabelFrame(main_frame, text="Target Directory", padding="10")
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(dir_frame, textvariable=self.target_directory, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_frame, text="Browse", command=self.browse_directory).pack(side=tk.LEFT, padx=5)
        
        # Decryption key
        key_frame = ttk.LabelFrame(main_frame, text="Decryption Key", padding="10")
        key_frame.pack(fill=tk.X, pady=5)
        
        key_text = tk.Text(key_frame, height=3, width=50)
        key_text.pack(fill=tk.BOTH, expand=True)
        
        def update_key(*args):
            self.decryption_key.set(key_text.get("1.0", tk.END).strip())
        
        key_text.bind("<KeyRelease>", update_key)
        
        # File extension
        ext_frame = ttk.LabelFrame(main_frame, text="Encrypted File Extension", padding="10")
        ext_frame.pack(fill=tk.X, pady=5)
        
        ttk.Entry(ext_frame, textvariable=self.file_extension, width=50).pack(fill=tk.X)
        ttk.Label(ext_frame, text="(e.g., .encrypted)", foreground="gray").pack(anchor=tk.W)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Load Key from File", command=self.load_key_from_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Decrypt Files", command=self.decrypt_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT, padx=5)
    
    def browse_directory(self):
        """Browse for target directory"""
        directory = filedialog.askdirectory()
        if directory:
            self.target_directory.set(directory)
    
    def load_key_from_file(self):
        """Load decryption key from file"""
        file_path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    key = f.read().strip()
                self.decryption_key.set(key)
                messagebox.showinfo("Success", "Key loaded successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load key: {str(e)}")
    
    def decrypt_files(self):
        """Decrypt files in target directory"""
        if not self.target_directory.get():
            messagebox.showerror("Error", "Please select a target directory")
            return
        
        if not self.decryption_key.get():
            messagebox.showerror("Error", "Please enter or load the decryption key")
            return
        
        try:
            # Validate key format
            key = self.decryption_key.get().encode()
            cipher = Fernet(key)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid decryption key: {str(e)}")
            return
        
        # Run decryption in separate thread to avoid freezing UI
        thread = threading.Thread(target=self._perform_decryption, args=(cipher,))
        thread.daemon = True
        thread.start()
    
    def _perform_decryption(self, cipher):
        """Perform actual decryption (runs in separate thread)"""
        try:
            target_dir = self.target_directory.get()
            ext = self.file_extension.get()
            decrypted_count = 0
            failed_count = 0
            
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    if file.endswith(ext):
                        file_path = os.path.join(root, file)
                        try:
                            # Read encrypted file
                            with open(file_path, 'rb') as f:
                                encrypted_data = f.read()
                            
                            # Decrypt file
                            decrypted_data = cipher.decrypt(encrypted_data)
                            
                            # Get original filename (remove extension)
                            original_name = file_path[:-len(ext)]
                            
                            # Write decrypted data to original filename
                            with open(original_name, 'wb') as f:
                                f.write(decrypted_data)
                            
                            # Delete encrypted file
                            os.remove(file_path)
                            decrypted_count += 1
                        except Exception as e:
                            print(f"Error decrypting {file_path}: {e}")
                            failed_count += 1
            
            # Show results
            result_msg = f"Decryption Complete!\n\nSuccessfully decrypted: {decrypted_count} files"
            if failed_count > 0:
                result_msg += f"\nFailed: {failed_count} files"
            
            self.root.after(0, lambda: messagebox.showinfo("Success", result_msg))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Decryption failed: {str(e)}"))


if __name__ == "__main__":
    root = tk.Tk()
    app = RansomwareDecrypter(root)
    root.mainloop()
