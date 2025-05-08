import os
import sys
import time
import requests
import tkinter as tk
from tkinter import messagebox

REW_API_BASE_URL = "http://localhost:4735"
WAV_STIMULUS_FILENAME = "1MMeasSweep_0_to_24000_-12_dBFS_48k_Float_L_refR.wav"

def get_script_directory():
    return os.path.dirname(os.path.abspath(__file__))

def get_sample_count():
    try:
        response = requests.get(f"{REW_API_BASE_URL}/measurements")
        response.raise_for_status()
        return len(response.json())
    except requests.RequestException as e:
        print(f"REW API Error: {e}")
        return -1

def start_capture(channel, position, status_callback=None):
    sample_name = f"{channel}_pos{position}"
    mlp_filename = f"{channel}.mlp"
    full_path_mlp = os.path.join(get_script_directory(), mlp_filename)
    stimulus_path = os.path.join(get_script_directory(), WAV_STIMULUS_FILENAME)

    try:
        requests.post(f"{REW_API_BASE_URL}/measure/measurement-mode", json="Single").raise_for_status()
        requests.post(f"{REW_API_BASE_URL}/measure/naming", json={"title": sample_name}).raise_for_status()
        requests.post(f"{REW_API_BASE_URL}/measure/playback-mode", json="From file").raise_for_status()
        requests.post(f"{REW_API_BASE_URL}/measure/timing/reference", json="Acoustic").raise_for_status()
        requests.post(f"{REW_API_BASE_URL}/measure/file-playback-stimulus", json=stimulus_path).raise_for_status()
        requests.post(f"{REW_API_BASE_URL}/measure/command", json={"command": "SPL"}).raise_for_status()

        if status_callback:
            status_callback(f"Measurement started: {sample_name}")
        else:
            print(f"Measurement started: {sample_name}")

        os.startfile(full_path_mlp)

    except requests.RequestException as e:
        err_msg = f"Error starting measurement '{sample_name}': {e}"
        if status_callback:
            messagebox.showerror("Measurement Error", err_msg)
        else:
            print(err_msg)
    except Exception as e:
        err_msg = f"Playback error for '{mlp_filename}': {e}"
        if status_callback:
            messagebox.showerror("Playback Error", err_msg)
        else:
            print(err_msg)

def run_measurement(mode, channels, num_positions, status_callback=print):
    channels = [ch.strip() for ch in channels.split(",")]
    try:
        num_positions = int(num_positions)
    except ValueError:
        status_callback("Number of positions must be an integer.")
        return

    status_callback("Make sure REW is running and mic is at position 0 (MLP).")
    if mode == "cli":
        input("Press Enter to continue...")

    initial_count = get_sample_count()
    if initial_count == -1:
        return

    for pos in range(num_positions):
        if pos != 0:
            input(f"Move mic to position {pos} and press Enter to continue...")

        for ch in channels:
            sample_name = f"{ch}_pos{pos}"
            status_callback(f"Capturing {sample_name}...")

            start_capture(ch, pos, status_callback)
            time.sleep(30)  # Initial wait increased to 30 seconds

            waited = 0
            timeout = 60
            while waited < timeout:
                count = get_sample_count()
                if count == -1:
                    return
                if count > initial_count:
                    initial_count = count
                    break
                status_callback(f"Waiting for {sample_name}... ({waited + 30}s)")
                time.sleep(5)
                waited += 5
            else:
                status_callback(f"Timeout waiting for {sample_name}. Exiting.")
                return

    status_callback("All samples complete. Please follow OCA's instructions for running A1 Evo Neuron next.")

def cli():
    if len(sys.argv) != 3:
        print("\nUsage: python script.py <comma_separated_channels> <number_of_positions>")
        print("Example: python script.py FL,FR,C,Sub 8\n")
        sys.exit(1)

    channels = sys.argv[1]
    positions = sys.argv[2]
    run_measurement("cli", channels, positions)

def launch_gui():
    def on_start():
        ch = channel_entry.get()
        pos = position_entry.get()
        if not ch or not pos:
            messagebox.showwarning("Missing Info", "Please enter both fields.")
            return
        run_measurement("gui", ch, pos, update_status)

    def update_status(msg):
        status_text.set(msg)
        root.update_idletasks()

    root = tk.Tk()
    root.title("Neuron Companion, by Hyacin and ChatGPT")
    root.geometry("500x250")
    root.resizable(False, False)

    tk.Label(root, text="Audio Channels (comma-separated):").pack(pady=(20, 5))
    channel_entry = tk.Entry(root, width=50)
    channel_entry.pack()

    tk.Label(root, text="Number of Positions:").pack(pady=(15, 5))
    position_entry = tk.Entry(root, width=10)
    position_entry.pack()

    tk.Button(root, text="Start Measurement", command=on_start, bg="#4CAF50", fg="white", width=20).pack(pady=20)

    status_text = tk.StringVar()
    status_text.set("Waiting to start...")
    tk.Label(root, textvariable=status_text, fg="blue").pack()

    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        cli()
    else:
        launch_gui()