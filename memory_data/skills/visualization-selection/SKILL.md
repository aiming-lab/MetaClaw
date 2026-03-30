---
name: visualization-selection
description: "Use this skill when asked to create a chart, plot, graph, or dashboard — e.g. 'visualize this data', 'make a chart of trends', or 'show this distribution'. Provides a lookup table mapping data goals (compare categories, show distribution, trend over time, correlation, part-to-whole) to the right chart type, plus principles for axes, color, and avoiding misleading 3D or truncated charts."
---

# Visualization Selection Guide

| Goal | Chart Type |
|------|------------|
| Compare categories | Bar chart (horizontal if many labels) |
| Show distribution | Histogram, box plot, violin plot |
| Show trend over time | Line chart |
| Show correlation | Scatter plot, heatmap |
| Show part-to-whole | Pie (<=5 slices), stacked bar |

**Principles:**
- Label axes and include units.
- Use color purposefully — not just for decoration.
- Avoid 3D charts; they distort perception.
- Start y-axis at 0 for bar charts (truncated bars mislead).
- Use a colorblind-safe palette (e.g., `viridis`, `colorbrewer`).
