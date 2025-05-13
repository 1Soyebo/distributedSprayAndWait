import matplotlib.pyplot as plt

# Data provided
data = ["1, 40.452583", "4, 15.203067", "8, 16.171633", "16, 14.163778"]

# Parse the data into x and y values
x = []
y = []
for entry in data:
    x_val, y_val = entry.split(", ")
    x.append(int(x_val))
    y.append(float(y_val))

# Plotting the bar chart
plt.figure(figsize=(8, 5))
plt.bar(x, y, width=1.0, color='skyblue', edgecolor='black')
plt.xlabel("Values of K")
plt.ylabel("Time (seconds)")
plt.title("Delivery Time vs Values of K")
plt.xticks(x)
plt.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()