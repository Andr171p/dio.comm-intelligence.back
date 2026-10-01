import asyncio

from dotenv import load_dotenv

from src.infra.services.iam import SrvIamClient, SrvIamConfig

load_dotenv()

ACCESS_TOKEN = "<...>"

iam_config = SrvIamConfig()  # type: ignore
iam_client = SrvIamClient(iam_config)


async def main() -> None:
    auth = await iam_client.authenticate(ACCESS_TOKEN)
    print(auth)
    await iam_client.close()


if __name__ == "__main__":
    asyncio.run(main())
