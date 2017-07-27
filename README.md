# Python Kubernetes Initializer

This project is a library to aid in writing [initializers for Kubernetes 1.7](https://kubernetes.io/docs/admin/extensible-admission-controllers/).

## Getting Started

This requires Python 3. On OS X, it also [requires having OpenSSL at least version 1.0](https://github.com/kubernetes-incubator/client-python/tree/6b555de1c7a1a291d0afcba91823ff419a044ca0#sslerror-on-macos). You can check your current OpenSSL version by running:
```
python3 -c "import ssl; print(ssl.OPENSSL_VERSION)"
```

You also almost certainly want to set up a virtual environment using [`venv`](https://docs.python.org/3/library/venv.html) or another tool.
