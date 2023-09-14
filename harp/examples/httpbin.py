from harp import ProxyFactory

proxy = ProxyFactory()

proxy.add("http://localhost:8080/", port=4000, name="httpbin")

if __name__ == "__main__":
    proxy.run()
