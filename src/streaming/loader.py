"""
Loads the AI4I dataset for streaming.
"""
import pandas as pd
import os

def load_dataset(path=None):
	if path is None:
		# Default path
		path = os.path.join(os.path.dirname(__file__), '../../data/ai4i_dataset.csv')
	df = pd.read_csv(path)
	df = df.dropna()
	return df
# Data loader for streaming AI4I dataset
