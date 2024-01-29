# Welcome to Blockingdom
## Installation Steps
`git clone https://github.com/LMCuber/BlockingdomGPUAccel
pip install noise pygame-ce psutil numpy pillow translatepy googletrans pandas line_profiler pymunk pycountry`

If you're on Windows, there is a chance that the `noise` module doesn't import as intended and you get an error similar to this one: `error: Microsoft Visual C++ 14.0 is required. Get it with "Microsoft Visual C++ Build Tools": https://visualstudio.microsoft.com/downloads/`
Until I switch to another noise library, you must install the latest Visual Studio IDE and make sure to tick the boxes that will install you the Visual C++ tools.

Lastly, since this project depends on the `pyengine` package I'm developing, you must:
`git clone https://github.com/LMCuber/pyengine`
And then in the root directory, run `pip install .`, which will install the package with `pip` and put it into your `site-packages` folder. No further tinkering is needed.

When the installation steps have been executed, enter `python main.py` from the root directory of the Blockingdom project. (Depending on your OS, `python3 main.py` might be the correct command. Especially if you have multiple Python versions installed on your machine.)
