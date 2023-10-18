""" Manual action in ArcGIS Pro: Raster calculater"""
# TODO update to code

output_raster = arcpy.ia.RasterCalculator(
    expression='("dsm_025m_int_100x"- "dtm_025m_int_100x")/100'
)
output_raster.save(
    r"<<project_folder>>\data\kristiansand\general\kristiansand_hoydedata.gdb\dsm_dtm_025m_float"
)
