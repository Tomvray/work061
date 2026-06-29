import pandas as pd

df_concat = pd.DataFrame(columns=["app_id", "year"])

for year in range(2008, 2019):
    df = pd.read_csv(f"../data/list_apps/list_{year}.txt")
    #name column "app_id" and remove ".json" suffix
    df.columns = ["app_id"]
    df["app_id"] = df["app_id"].str.replace(".json", "")
    df["year"] = year
    print(f"{year}: {len(df)} apps")
    print(df.head())
    df_concat = pd.concat([df_concat, df], ignore_index=True)

print(f"Total: {len(df_concat)} apps")
print(df_concat.head())
df_concat.to_csv("../data/list_apps/list_all.csv", index=False)
df_concat.to_csv("database/list_apps.csv", index=False)