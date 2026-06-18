import pandas as pd

df = pd.read_csv("data/processed/training_data.csv")

print("\nDATASET SHAPE")
print(df.shape)

print("\nCOLUMNS")
print(df.columns.tolist())

print("\nFIRST 5 ROWS")
print(df.head())

print("\nTARGET STATISTICS")
print(df["target_5d_return"].describe())
