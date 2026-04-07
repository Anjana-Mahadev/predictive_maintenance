"""
Simulates real-time streaming of sensor data with a sliding window.
"""
import time
from collections import deque
from loader import load_dataset

class StreamingSimulator:
	def __init__(self, window_size=10, interval=1.0):
		self.window_size = window_size
		self.interval = interval
		self.data = load_dataset()
		self.buffer = deque(maxlen=window_size)
		self.idx = 0

	def stream(self):
		for _, row in self.data.iterrows():
			self.buffer.append(row)
			self.idx += 1
			yield list(self.buffer)
			time.sleep(self.interval)

	def reset(self):
		self.buffer.clear()
		self.idx = 0
# Simulates real-time streaming of sensor data
