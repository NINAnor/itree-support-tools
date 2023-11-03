from setuptools import find_packages, setup

requirements = [
    # package requirements go here
]

setup(
    name="itree-support-tools",
    version="0.1.0",
    description="Tools for data preparation of iTree projects and extrapolation of iTree results.",
    license="MIT",
    author="willeke acampo",
    author_email="willeke.acampo@nina.no",
    url="https://github.com/ac-willeke/itree-support-tools",
    packages=find_packages(),
    install_requires=requirements,
)
