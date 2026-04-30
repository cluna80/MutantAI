import pandas as pd

def calculate_compound_interest(principal, rate, time):
    return principal * (1 + rate) ** time - principal


if __name__ == '__main__':
    print('Compound Interest Calculator')
    print('-' * 25)
    
    data = [
        [1000, 0.05, 1],
        [1000, 0.05, 3],
        [1000, 0.05, 5],
        [1000, 0.07, 10],
        [2000, 0.04, 15]
    ]
    
    df = pd.DataFrame(data, columns=['Principal', 'Rate', 'Time'])
    df['Interest'] = df.apply(lambda row: calculate_compound_interest(row['Principal'], row['Rate'], row['Time']), axis=1)
    
    print(df.to_string(index=False))
