from harp import ProxyFactory

proxy = ProxyFactory(
    settings={
        "storage": {
            "type": "in_memory",
            "database": {
                "max_size": 100,
            },
        }
    }
)

proxy.add("https://api-adresse.data.gouv.fr/", port=8000, name="api-adresse")
proxy.add("https://api-adresse.data.gouv.fr/", port=8001, name="api-adresse (2)")

if __name__ == "__main__":
    proxy.run()
