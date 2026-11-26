import pcbnew
for lib,n in [('SmartVioV25','TI_RNM0015A_TPS63070'),('SmartVioV25','TSOT-23-8'),('SmartVioV25','TI_RGT0016C_BQ24074_EP17'),('SmartVioV25','TI_RPW0010A_TPS259470'),('SmartVioV26','TI_DDC0006A_Official')]:
    f=pcbnew.FootprintLoad('/work/r4/footprints/%s.pretty'%lib,n); print(n, f is not None, len(f.Pads()) if f else '')
