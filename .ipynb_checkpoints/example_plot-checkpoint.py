import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # use non-interactive backend for script
import matplotlib.pyplot as plt
import seaborn as sns


def main():
    workspace_csv = 'International_Education_Costs.csv'
    if not os.path.exists(workspace_csv):
        print(f"CSV not found: {workspace_csv}")
        return

    df = pd.read_csv(workspace_csv)
    print(f"Loaded {len(df)} rows; columns: {list(df.columns)}")

    sns.set_theme(style='whitegrid')

    # Try to detect numeric columns; coerce object columns that look numeric
    numeric_cols = df.select_dtypes(include='number').columns.tolist()
    if not numeric_cols:
        for col in df.columns:
            if df[col].dtype == object:
                # remove common thousands separators then coerce
                coerced = pd.to_numeric(df[col].str.replace(',','').str.replace(' ','').str.replace('$',''), errors='coerce')
                if coerced.notna().sum() > 0:
                    df[col] = coerced
        numeric_cols = df.select_dtypes(include='number').columns.tolist()

    out_png = 'example_plot.png'
    plt.clf()
    plt.figure(figsize=(10, 6))

    if {'Country', 'TotalCost'}.issubset(df.columns):
        top = df.sort_values('TotalCost', ascending=False).head(15)
        sns.barplot(data=top, x='TotalCost', y='Country', palette='viridis')
        plt.title('Top 15 Countries by Total Cost')
        plt.xlabel('Total Cost')
        plt.tight_layout()
        plt.savefig(out_png)
        print(f"Saved bar plot to {out_png}")
        return

    # Fallback: histogram of the first numeric column
    if numeric_cols:
        col = numeric_cols[0]
        sns.histplot(df[col].dropna(), bins=30, kde=False, color='tab:blue')
        plt.title(f'Histogram of {col}')
        plt.xlabel(col)
        plt.tight_layout()
        plt.savefig(out_png)
        print(f"Saved histogram of '{col}' to {out_png}")
        return

    print('No suitable numeric columns found to plot. Preview:')
    print(df.head().to_string())


if __name__ == '__main__':
    main()
