import pandas as pd

df = pd.read_csv("../data/oa/citations.csv")
print(df.head())

print(df.iloc[16541])