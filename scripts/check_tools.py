from crewai_tools import FileWriterTool, FileReadTool
fw = FileWriterTool()
fr = FileReadTool()
print("FileWriterTool:")
print("  description:", fw.description)
print("  inputs:", fw.inputs)
print("FileReadTool:")
print("  description:", fr.description)
print("  inputs:", fr.inputs)
