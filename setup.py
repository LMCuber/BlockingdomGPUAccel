from setuptools import setup, find_packages


setup(
    include_package_data=True,
    name="Blockingdom",
    version="0.0.1",
    description="Asd",
    author="LMCuber",
    author_email="leo.bozkir@outlook.com",
    packages=find_packages(),
    install_requires=[
        "noise", "pygame-ce", "psutil", "numpy", "pillow", "translatepy", "googletrans", "pandas", "line_profiler", "pymunk",
    ],
)
