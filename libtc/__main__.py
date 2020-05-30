import click
from tabulate import tabulate

from libtc import move_torrent, parse_libtc_url


@click.group()
@click.argument("client_url")
@click.pass_context
def cli(ctx, client_url):
    ctx.ensure_object(dict)
    ctx.obj["client"] = parse_libtc_url(client_url)


@cli.command()
@click.option("--active", is_flag=True, help="Show only active torrents")
@click.pass_context
def list(ctx, active):
    client = ctx.obj["client"]
    if active:
        torrents = client.list_active()
    else:
        torrents = client.list()
    torrents = sorted(
        [(t.infohash, t.name) for t in torrents], key=lambda x: x[1].lower()
    )
    print(tabulate(torrents, headers=["Infohash", "Name"], tablefmt="presto"))


@cli.command()
@click.argument("infohash")
@click.pass_context
def start(ctx, infohash):
    client = ctx.obj["client"]
    client.start(infohash)
    print(f"Started {infohash}")


@cli.command()
@click.argument("infohash")
@click.pass_context
def stop(ctx, infohash):
    client = ctx.obj["client"]
    client.stop(infohash)
    print(f"Stopped {infohash}")


@cli.command()
@click.argument("infohash")
@click.pass_context
def remove(ctx, infohash):
    client = ctx.obj["client"]
    client.remove(infohash)
    print(f"Removed {infohash}")


@cli.command()
@click.pass_context
def test_connection(ctx):
    client = ctx.obj["client"]
    if client.test_connection():
        print("Connected to client successfully")
    else:
        print("Failed to connect")


@cli.command()
@click.argument("infohash")
@click.argument("target_client_url")
@click.pass_context
def move(ctx, infohash, target_client_url):
    source_client = ctx.obj["client"]
    target_client = parse_libtc_url(target_client_url)
    move_torrent(infohash, source_client, target_client)
    print(f"Moved {infohash}")


if __name__ == "__main__":
    cli()
