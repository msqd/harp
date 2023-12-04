from harp import ProxyFactory

proxy = ProxyFactory()

proxy.add(4000, "http://localhost:8080/", name="httpbin")

if __name__ == "__main__":
    proxy.serve()
