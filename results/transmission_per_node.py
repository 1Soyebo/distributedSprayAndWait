import matplotlib.pyplot as plt
import numpy as np
import ast

# Provided data
data = {
    "1": "[1, 2, 2, 3]",
    "2": "[0, 1, 1, 1]",
    "3": "[0, 0, 0, 0]",
    "4": "[0, 0, 0, 0]"
}

# Parse the string lists into actual Python lists
parsed_data = {node: ast.literal_eval(transmissions) for node, transmissions in data.items()}

# x-axis labels for different k values
k_values = [1, 4, 8, 16]
x = np.arange(len(k_values))  # the label locations
width = 0.2  # the width of the bars

# Plotting
fig, ax = plt.subplots(figsize=(10, 6))

# Plot each node's transmissions as a set of bars
for i, (node, transmissions) in enumerate(parsed_data.items()):
    ax.bar(x + i * width, transmissions, width, label=f'Node {node}')

# Labels and formatting
ax.set_xlabel('k Value')
ax.set_ylabel('Transmissions')
ax.set_title('Transmissions per Node at Different k Values')
ax.set_xticks(x + width * (len(parsed_data) - 1) / 2)
ax.set_xticklabels(k_values)
ax.legend()
ax.grid(axis='y', linestyle='--', alpha=0.7)

plt.tight_layout()
plt.show()
