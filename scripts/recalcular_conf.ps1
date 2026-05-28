param(
    [Parameter(Mandatory=$true)][string]$XmlPath,
    [string]$IrpfDir = "C:\Arquivos de Programas RFB\IRPF2026"
)

$ErrorActionPreference = "Stop"
cd $IrpfDir

.\jre\bin\java.exe -cp ".\irpf.jar;.\lib\*;.\lib-modulos\*" groovy.ui.GroovyMain -e "def xml=args[0]; def repo=serpro.ppgd.persistenciagenerica.RepositorioXMLDefault.getInstancia(); println repo.gerarHash(xml); repo.salvarHash(xml); println 'CONF_ATUALIZADO'" $XmlPath
