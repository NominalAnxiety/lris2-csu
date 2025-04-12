# lris2csu
A demo package for the LRIS2 Configurable Slit Unit, showcasing remote client objects, hardware servers, 
zmq communication (with support for mKTL developments). 

## Installation
#Install miniconda


mkdir ~/src  #or wherever
cd ~/src  #or wherever

git clone https://github.com/CaltechOpticalObservatories/lris2-csu.git
git clone https://github.com/CaltechOpticalObservatories/coo-ethercat.git
git clone -b develop https://github.com/baileyji/mKTL.git mktl
cd lris2-csu
conda env create -f environment.yml
conda activate lris2csu
pip install pysoem
pip install -e ./coo-ethercat
pip install -e ./mktl
pip install -e ./lris2-csu


### Requirements

- Python 3.12 or higher
- `pip` (ensure it's the latest version)
- `setuptools` 42 or higher (for building the package)
- `cooethercat`


### Where to look, how to use (for now)

#### iPython play

Take a look at `lris2-csu/examples/demo.py` for local ipython commanding. 

`sudo /home/l2dev/miniconda3/bin/conda run -n lris2csu --no-capture-output ipython`


#### daemon/client ecosystem

Take a look at Take a look at lris2-csu/examples/mktl_play.py for remote control via "mktl" commanding. Note that this would need spinning up:
`sudo ip link set dev eno1  up`
- Three Terminals:
  - `conda run -n lris2csu python ~/src/mKTL/mktl/registry.py`
  - `sudo /home/l2dev/miniconda3/bin/conda run -n lris2csu --no-capture-output python ~/src/lris2-csu/lris2csu/manager.py --eth eno1 --cfg ~/src/lris2-csu/lris2csu/config/csu.yaml`
  - `conda run -n lris2csu python ~/src/mKTL/mktl/registry.py`
- Command Terminal
  - Start up ipython somewhere and instantiate `lris2-csu.remote.CSURemote()`


/Users/jibailey/src/lris2-csu/lris2csu/manager.py