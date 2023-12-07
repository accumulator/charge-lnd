def calculate_slices(max_value, current_value, num_slices):
    # Calculate the size of each slice
    slice_size = max_value // num_slices

    # Find the slice number containing the current_value
    current_slice = min(current_value // slice_size, num_slices - 1)

    # Determine the upper value of the slice closest to current without going over
    slice_point = min((current_slice + 1) * slice_size - 1, max_value)

    return slice_point

# Example usage
max_value = 1000000
current_value = 1000000
num_slices = 10

slice_point = calculate_slices(max_value, current_value, num_slices)

print(f"max: {max_value}, current: {current_value}, slices: {num_slices}")
print(f"slice_point: {slice_point}")