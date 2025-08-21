from helpers import fetch_multiple_series, get_msa_restaurant_series_ids
import os
from pathlib import Path

cookies = {
    'cookiesession1': '678A3E1FBF92D0C91576F31EC42DE74B',
    '_ga_D5DWMDR6J0': 'GS2.1.s1754999681$o2$g1$t1754999691$j50$l0$h0',
    'ak_bmsc': '9BA952ADCF24001D0F1753D2998405FA~000000000000000000000000000000~YAAQlGRCF787e62YAQAAHFLlxxxb402vh1DArNCSgQ/AyhOMJEh/3YfSMfOcJvAJUQTPMEO0hIHJ1BEue65PnjwwRCXyU7yNk/1w/fLuhl6ybEQgFVSWo1SaGJsg1R/fL8qN+2VwUXNQUx+UQ0k+N9gtx8W5ZyZVE7u/PkBeHYpcLkdlihKtsesYjSZ+2dnmgM7UNMlvdv/TlOcuGM0ARZeKvbBSLTTMqYdYROQGPZUWsvMruAMaeiL++SBl9ECSGrUDPizbZSM6QNM4Ortb8/45lpEX3Hb+7ng/mvu0foql+dD1rKKM78z6/lLq0nloxILqnQ24mEFV1xdeakG2Oup6tKXNv8CSJx7mAlhf/na8Qr6C8sAFuLj3Q7eSvRmGI5km8oMmJao2u835e+ljlg==',
    '_gid': 'GA1.2.862338100.1755700354',
    '_abck': '67314D68E6517D3A89385D60BE020FF4~0~YAAQlGRCF6Xzia2YAQAAligvyA5Z34z5jvYFDLd79dgDaCo2rDIrsXpesxbx+rdFwXbtAQa9uixYHjsTRejbIt74LtwdODvSEQ8ES1BtwvKqEFbfP2SLDdIKlz2yVCfqhEYWJGWr9p4/ZymtEcuEuABgVHxdgFzt864/EZOuqt/CTh/SmQTHTo/LH8roFUEKf8pMzDCQGK3U6yrpfWAX8gbllCArJwvekm607x+7YzcKO0ovQP3lVbpDgYnYvTrZSAqP2WHxnqBZNtDU1KpLzFwX1UsxX4/3gb6AqIx4+nGnksm5MoTj1hC8EL9RXBoK+vqoZabE4V7h74JqIxwelBYSoSrYffckJUQrOM4Ar8S+cLAgxwdfIk2WgcuJmm1b4OcnmXt4Z5LNcAd12GBfSxXY+IFs+dFH3f3p58J/QdGzDYX16zQNWEU6l5XcJHFVRE5gqovHmCVzafVkfN0SeQIQKOmw2mzMyM0W6jJtuUXIeyDPJfr2G2ATvEaTaDIZvy0ddy62kNjXvnBgvaTRQ2mL22XHYJ6KV3lAgpUdhv+VGTR3hUHUV1bVVhgwUFUAEyxNhEQ/l/YbQFYd4wlaC5Uf8TQOh3Nu4T8yzDj4GqHe9jBDLBZlfOmPPnXtKMKbGutRMphU1c6BtpGKBWgUssSW4ijeU8EzyvlNdSPHZSuiBrpYgPYGwrYRoHWS1JD/gGT+tmKi5VjZUyOkGhNRIafmsNtB48xDiMbAh3eOIIoS4THcyCkEndJQQGySSBggRaRh5cbe2SfEd3kBndkaeKo=~-1~-1~-1',
    'bm_sz': '2604CDC3A650A8521F9D26F36366D83D~YAAQlGRCFwAZjq2YAQAAJUBEyByeVtn9Id9c5jLKlW6GkbfnVJqu+1Zvn6wDgjgU+aps5yYQ5ixGwg/3oy8ACo2x5GYfC18fHUOp/Is/6q0UjIngIeKziZ4Tg1aLsyH6TKviRjX+omxyzd1lbQyMM/Sr2iuP4G2HrkIQGho/yRPzksnWUsHvGo9+9nTwWcoKZKh5Mpk7XqVGejLi5D190NDBrXuoLC7PicKIY2/smz8za41fOkGSKMAjtFEWS8nR9fmgW94bs9PHvcoLhzmRtMbsHEkFfd29rdTUyZklV/TIncf9+QlpA7MOih7DYz0Imx+ATbJTeDarSfI/T50/uNe3uKki/f96lCZflL5rVI7fyfVtaCOxHji2KPj0BgOdmsyk4Q74YqWXkRjjS8hYk///4hkgJgHQCgp7h1l4JPgR+qJL9GOhxahlrt8Um/UtZ4aOfHv+7uhpmglUR5qE/6jRRbV9uAqrK2Bi7gIKmuLJTR7/fOXBmN2YhIQuhEcD/Nx9S3uXreXFgtBEnnR4YweQfnSAZmFgC9UrIk0xzS+Y9YaCOEDcSwx/Kmak~4408121~3486276',
    '_gat_UA-9926151-28': '1',
    '_ga_M8THG4VKKZ': 'GS2.1.s1755700353$o41$g1$t1755706575$j60$l0$h0',
    '_ga': 'GA1.1.401027326.1749752764',
    'bm_sv': 'C0F5989038A439D16D139CD3D2DDD6FA~YAAQlGRCF1Iajq2YAQAA30REyByrxtTw+/d9sDddJZ8WsHZPs3MFTiThoul5Dp0DgOnXdl1L5uKYiqPP4/KARgnSzMrjHvQWOFF4+PDFc88wULmk/e4YKnr+JLOcP+vDNV/ypAjYxYT0rVulZErBqtretnjkQqxqSBQ8E0iWmEknpLRJ/cwf6U/n7mTvzKZvbDv4MO6g0SWghO5kQUndpBPZDoMIL2B5/ZnR1aDCWarpQEUcx9fk4NypvuanrnfUkorSaCDn~1',
}

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'en-US,en;q=0.9',
    'cache-control': 'max-age=0',
    'priority': 'u=0, i',
    'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
    # 'cookie': 'cookiesession1=678A3E1FBF92D0C91576F31EC42DE74B; _ga_D5DWMDR6J0=GS2.1.s1754999681$o2$g1$t1754999691$j50$l0$h0; ak_bmsc=9BA952ADCF24001D0F1753D2998405FA~000000000000000000000000000000~YAAQlGRCF787e62YAQAAHFLlxxxb402vh1DArNCSgQ/AyhOMJEh/3YfSMfOcJvAJUQTPMEO0hIHJ1BEue65PnjwwRCXyU7yNk/1w/fLuhl6ybEQgFVSWo1SaGJsg1R/fL8qN+2VwUXNQUx+UQ0k+N9gtx8W5ZyZVE7u/PkBeHYpcLkdlihKtsesYjSZ+2dnmgM7UNMlvdv/TlOcuGM0ARZeKvbBSLTTMqYdYROQGPZUWsvMruAMaeiL++SBl9ECSGrUDPizbZSM6QNM4Ortb8/45lpEX3Hb+7ng/mvu0foql+dD1rKKM78z6/lLq0nloxILqnQ24mEFV1xdeakG2Oup6tKXNv8CSJx7mAlhf/na8Qr6C8sAFuLj3Q7eSvRmGI5km8oMmJao2u835e+ljlg==; _gid=GA1.2.862338100.1755700354; _abck=67314D68E6517D3A89385D60BE020FF4~0~YAAQlGRCF6Xzia2YAQAAligvyA5Z34z5jvYFDLd79dgDaCo2rDIrsXpesxbx+rdFwXbtAQa9uixYHjsTRejbIt74LtwdODvSEQ8ES1BtwvKqEFbfP2SLDdIKlz2yVCfqhEYWJGWr9p4/ZymtEcuEuABgVHxdgFzt864/EZOuqt/CTh/SmQTHTo/LH8roFUEKf8pMzDCQGK3U6yrpfWAX8gbllCArJwvekm607x+7YzcKO0ovQP3lVbpDgYnYvTrZSAqP2WHxnqBZNtDU1KpLzFwX1UsxX4/3gb6AqIx4+nGnksm5MoTj1hC8EL9RXBoK+vqoZabE4V7h74JqIxwelBYSoSrYffckJUQrOM4Ar8S+cLAgxwdfIk2WgcuJmm1b4OcnmXt4Z5LNcAd12GBfSxXY+IFs+dFH3f3p58J/QdGzDYX16zQNWEU6l5XcJHFVRE5gqovHmCVzafVkfN0SeQIQKOmw2mzMyM0W6jJtuUXIeyDPJfr2G2ATvEaTaDIZvy0ddy62kNjXvnBgvaTRQ2mL22XHYJ6KV3lAgpUdhv+VGTR3hUHUV1bVVhgwUFUAEyxNhEQ/l/YbQFYd4wlaC5Uf8TQOh3Nu4T8yzDj4GqHe9jBDLBZlfOmPPnXtKMKbGutRMphU1c6BtpGKBWgUssSW4ijeU8EzyvlNdSPHZSuiBrpYgPYGwrYRoHWS1JD/gGT+tmKi5VjZUyOkGhNRIafmsNtB48xDiMbAh3eOIIoS4THcyCkEndJQQGySSBggRaRh5cbe2SfEd3kBndkaeKo=~-1~-1~-1; bm_sz=2604CDC3A650A8521F9D26F36366D83D~YAAQlGRCFwAZjq2YAQAAJUBEyByeVtn9Id9c5jLKlW6GkbfnVJqu+1Zvn6wDgjgU+aps5yYQ5ixGwg/3oy8ACo2x5GYfC18fHUOp/Is/6q0UjIngIeKziZ4Tg1aLsyH6TKviRjX+omxyzd1lbQyMM/Sr2iuP4G2HrkIQGho/yRPzksnWUsHvGo9+9nTwWcoKZKh5Mpk7XqVGejLi5D190NDBrXuoLC7PicKIY2/smz8za41fOkGSKMAjtFEWS8nR9fmgW94bs9PHvcoLhzmRtMbsHEkFfd29rdTUyZklV/TIncf9+QlpA7MOih7DYz0Imx+ATbJTeDarSfI/T50/uNe3uKki/f96lCZflL5rVI7fyfVtaCOxHji2KPj0BgOdmsyk4Q74YqWXkRjjS8hYk///4hkgJgHQCgp7h1l4JPgR+qJL9GOhxahlrt8Um/UtZ4aOfHv+7uhpmglUR5qE/6jRRbV9uAqrK2Bi7gIKmuLJTR7/fOXBmN2YhIQuhEcD/Nx9S3uXreXFgtBEnnR4YweQfnSAZmFgC9UrIk0xzS+Y9YaCOEDcSwx/Kmak~4408121~3486276; _gat_UA-9926151-28=1; _ga_M8THG4VKKZ=GS2.1.s1755700353$o41$g1$t1755706575$j60$l0$h0; _ga=GA1.1.401027326.1749752764; bm_sv=C0F5989038A439D16D139CD3D2DDD6FA~YAAQlGRCF1Iajq2YAQAA30REyByrxtTw+/d9sDddJZ8WsHZPs3MFTiThoul5Dp0DgOnXdl1L5uKYiqPP4/KARgnSzMrjHvQWOFF4+PDFc88wULmk/e4YKnr+JLOcP+vDNV/ypAjYxYT0rVulZErBqtretnjkQqxqSBQ8E0iWmEknpLRJ/cwf6U/n7mTvzKZvbDv4MO6g0SWghO5kQUndpBPZDoMIL2B5/ZnR1aDCWarpQEUcx9fk4NypvuanrnfUkorSaCDn~1',
}

final_df = fetch_multiple_series(get_msa_restaurant_series_ids(), cookies, headers)


# Absolute path to the root of the project (i.e., Paper3/)
project_root = Path(__file__).resolve().parents[2]

# Path to Data folder
data_dir = project_root / 'Data'
data_dir.mkdir(parents=True, exist_ok=True)  # create if not exists


filename = "msa_full_service_rest.csv"
output_path = data_dir / filename
final_df.to_csv(output_path, index=False)

