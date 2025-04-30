import os
from collections import defaultdict


def find_duplicate_leaf_folders(base_directory):
    """Find duplicate leaf folder names under the specified base directory."""
    folder_names = defaultdict(list)
    duplicates = []

    for root, dirs, files in os.walk(base_directory):
        # Ignore the 'pages' directory
        if 'pages' in root.split(os.sep):
            continue

        # Check if the current directory is a leaf directory
        if not dirs:
            folder_name = os.path.basename(root)
            folder_names[folder_name].append(root)

    # Collect duplicates
    for folder_name, paths in folder_names.items():
        if len(paths) > 1:
            duplicates.append(paths)

    return folder_names, duplicates


def summarize_duplicates(duplicates):
    """Summarize the duplicate folders."""
    summary = defaultdict(int)
    for paths in duplicates:
        count = len(paths)
        summary[count] += 1

    return summary


def main():
    # Convert the base directory to an absolute path
    base_directory = os.path.abspath('json_data')
    folder_names, duplicates = find_duplicate_leaf_folders(base_directory)

    total_folders = sum(len(paths) for paths in folder_names.values())
    print(f"Total number of folders: {total_folders}")

    if duplicates:
        print("\nDuplicate leaf folders found:")
        for paths in duplicates:
            print(f"Duplicate folder name found in:")
            for path in paths:
                print(path)
            print()

        # Summarize duplicates
        summary = summarize_duplicates(duplicates)
        print("Summary of duplicates:")
        for count, num_folders in sorted(summary.items()):
            print(f"{num_folders} folders with {count} duplicates")

        print("\nTotal folders with duplicates: ", len(duplicates))

        # Show full paths for folders with exactly 4 duplicates
        if 4 in summary:
            print("\nFolders with exactly 4 duplicates:")
            for paths in duplicates:
                if len(paths) == 4:
                    for path in paths:
                        print(path)
                    print()
    else:
        print("No duplicate leaf folders found.")


if __name__ == "__main__":
    main()
