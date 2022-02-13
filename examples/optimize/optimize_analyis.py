#!/usr/bin/env python3

import pandas as pd

df = pd.read_csv("data/optimize_output.csv")
df = df.sort_values("cost") 
print(df)

