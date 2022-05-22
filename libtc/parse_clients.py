from .clients import TORRENT_CLIENT_MAPPING, parse_libtc_url


def parse_clients_from_toml_dict(toml_dict):
    clients = {}

    for name, config in toml_dict["clients"].items():
        display_name = config.pop("display_name", name)
        client_url = config.pop("client_url", None)
        if client_url:
            client = parse_libtc_url(client_url)
        else:
            client_type = config.pop("client_type")
            client_cls = TORRENT_CLIENT_MAPPING[client_type]
            client = client_cls(**config)
        clients[name] = {
            "display_name": display_name,
            "client": client,
        }

    return clients
