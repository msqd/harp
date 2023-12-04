from harp import ProxyFactory

proxy = ProxyFactory(
    settings={
        # "storage": {
        #     "type": "sql_database",
        # }
    }
)

proxy.add(4000, "https://api-adresse.data.gouv.fr/", name="api-adresse")
proxy.add(4001, "https://api-adresse.data.gouv.fr/", name="api-adresse (2)")


if __name__ == "__main__":
    proxy.serve()
