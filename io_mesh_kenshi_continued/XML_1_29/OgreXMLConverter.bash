#!/bin/bash

#simple wrapper for running exe via Wine

# Get the directory of the script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Command to execute using Wine
WINE_COMMAND="OgreXMLConverter.exe"

# Run the Wine command with arguments
wine "$SCRIPT_DIR/$WINE_COMMAND" "$@"