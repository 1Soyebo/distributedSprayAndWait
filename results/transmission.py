import matplotlib.pyplot as plt

# Data provided
data = ["1, 1", "4, 3", "8, 3", "16, 4"]

# Parse the data into x and y values
x = []
y = []
for entry in data:
    x_val, y_val = entry.split(", ")
    x.append(int(x_val))
    y.append(int(y_val))

# Plotting the bar chart
plt.figure(figsize=(8, 5))
plt.bar(x, y, width=1.0, color='red', edgecolor='black')
plt.xlabel("Values of K")
plt.ylabel("Number of transmissions")
plt.title("Number of Transmissions vs Values of K")
plt.xticks(x)
plt.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()