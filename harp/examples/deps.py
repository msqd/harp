from harp import ProxyFactory

proxy = ProxyFactory()

proxy.add(9001, "https://pypi.org/", name="pypi")
proxy.add(9002, "https://registry.npmjs.org/", name="npm")

if __name__ == "__main__":
    proxy.serve()
