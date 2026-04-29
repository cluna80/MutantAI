import csv
from collections import Counter
import os

def is_numeric(value: str) -> bool:
    """
    Check if the given value can be converted to a float.
    
    :param value: The string value to check.
    :return: True if the value is numeric, False otherwise.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False

def load_csv(file_path: str) -> list[list[str]]:
    """
    Load a CSV file and validate its existence.
    
    :param file_path: The path to the CSV file.
    :return: A list of rows from the CSV file.
    :raises FileNotFoundError: If the file does not exist.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file {file_path} does not exist.")
    
    with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        return [row for row in reader]

def calculate_mean(data: list[float]) -> float:
    """
    Calculate the mean of a list of numbers.
    
    :param data: The list of numbers.
    :return: The mean value.
    """
    return sum(data) / len(data)

def calculate_median(data: list[float]) -> float:
    """
    Calculate the median of a list of numbers.
    
    :param data: The list of numbers.
    :return: The median value.
    """
    sorted_data = sorted(data)
    n = len(sorted_data)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_data[mid - 1] + sorted_data[mid]) / 2.0
    else:
        return sorted_data[mid]

def calculate_mode(data: list[float]) -> float:
    """
    Calculate the mode of a list of numbers.
    
    :param data: The list of numbers.
    :return: The mode value.
    """
    counter = Counter(data)
    max_count = max(counter.values())
    modes = [num for num, count in counter.items() if count == max_count]
    return modes[0]  # Return the first mode found

def show_statistics(rows: list[list[str]]) -> None:
    """
    Analyze and display statistics for numeric and text columns.
    
    :param rows: The list of rows from the CSV file.
    """
    if not rows:
        print("No data to analyze.")
        return
    
    headers = rows[0]
    data_rows = rows[1:]
    
    numeric_columns = {i: [] for i, header in enumerate(headers) if is_numeric(data_rows[0][i])}
    
    for row in data_rows:
        for col_index, value in enumerate(row):
            if col_index in numeric_columns:
                try:
                    numeric_columns[col_index].append(float(value))
                except ValueError:
                    print(f"Skipping non-numeric value '{value}' in column {headers[col_index]}")
    
    print("📊 CSV Analysis Results 📊")
    print("-" * 40)
    
    for col_index, values in numeric_columns.items():
        header = headers[col_index]
        if values:
            mean_value = calculate_mean(values)
            median_value = calculate_median(values)
            mode_value = calculate_mode(values)
            min_value = min(values)
            max_value = max(values)
            
            print(f"Column: {header}")
            print(f"  Mean: {mean_value:.2f}")
            print(f"  Median: {median_value:.2f}")
            print(f"  Mode: {mode_value:.2f}")
            print(f"  Min: {min_value:.2f}")
            print(f"  Max: {max_value:.2f}")
            print("-" * 40)
        else:
            print(f"No numeric data found in column: {header}")
            print("-" * 40)

if __name__ == "__main__":
    try:
        file_path = "data.csv"
        rows = load_csv(file_path)
        show_statistics(rows)
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")