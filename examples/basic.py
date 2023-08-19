from harp import ProxyFactory

proxy = ProxyFactory()

proxy.add("https://api-adresse.data.gouv.fr/", port=8000, name="api-adresse")
proxy.add("https://api-adresse.data.gouv.fr/", port=8001, name="api-adresse (2)")

if __name__ == "__main__":
    proxy.run()
