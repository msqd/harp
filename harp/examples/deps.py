from harp import ProxyFactory

proxy = ProxyFactory()

proxy.add("https://pypi.org/", port=9001, name="pypi")
proxy.add("https://registry.npmjs.org/", port=9002, name="npm")

if __name__ == "__main__":
    proxy.run()
