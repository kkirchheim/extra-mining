# script for exporting project specific environment variables
SM_ROOT=$(git rev-parse --show-toplevel)
export PYTHONPATH=$PYTHONPATH:$SM_ROOT/src