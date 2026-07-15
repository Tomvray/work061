import pandas as pd


# 1983
df = pd.read_csv("/workspace/g_claims_1983.tsv", sep="\t")
df['claim_number'] = df['claim_number'].astype('Int64')
df['claim_sequence'] = df['claim_sequence'].astype('Int64')
print(df.dtypes)
df.to_csv("/workspace/g_claims_1983_cleaned.tsv", sep="\t", index=False)
# 2001
df = pd.read_csv("/workspace/g_claims_2001.tsv", sep="\t")
print(df.shape)
df.dropna(inplace=True)
print(df.shape)
df.to_csv("/workspace/g_claims_2001_cleaned.tsv", sep="\t", index=False)
