from harp import ProxyFactory

proxy = ProxyFactory(ui=True)

proxy.add("https://api-adresse.data.gouv.fr/", port=8000)
proxy.add("https://api-adresse.data.gouv.fr/", port=8001)

if __name__ == "__main__":
    proxy.run()
