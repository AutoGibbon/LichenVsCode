<#
.SYNOPSIS
Install the Lichen theme into Notepad++ and switch Notepad++ dark mode to the Lichen theme and UI colours.

.DESCRIPTION
Copies Lichen.xml into <ConfigDir>\themes and sets the DarkMode GUIConfig in <ConfigDir>\config.xml.
Close Notepad++ first: it rewrites config.xml on exit and would discard the change.
config.xml is backed up to config.xml.lichen-backup before it is changed.

.PARAMETER ConfigDir
Notepad++ settings folder. Use the install folder instead of the default for a portable install or one that
contains doLocalConf.xml.
#>
param(
    [string]$ConfigDir = (Join-Path $env:APPDATA 'Notepad++')
)

$ErrorActionPreference = 'Stop'

if (Get-Process -Name 'notepad++' -ErrorAction SilentlyContinue) {
    throw 'Notepad++ is running. Close it and run this script again.'
}

$config = Join-Path $ConfigDir 'config.xml'
if (-not (Test-Path $config)) {
    throw "$config not found. Start and close Notepad++ once to create it, or pass -ConfigDir."
}

$themes = Join-Path $ConfigDir 'themes'
New-Item -ItemType Directory -Force $themes | Out-Null
Copy-Item (Join-Path $PSScriptRoot 'Lichen.xml') $themes -Force
Write-Host "Copied Lichen.xml to $themes"

# Custom colours are Win32 COLORREF values (0x00BBGGRR) written as decimal.
$darkMode = [ordered]@{
    enable                  = 'yes'
    enableWindowsMode       = 'no'
    colorTone               = '32'
    customColorTop          = '592392'
    customColorMenuHotTrack = '1908506'
    customColorActive       = '1908506'
    customColorMain         = '1184528'
    customColorError        = '1381674'
    customColorText         = '7371372'
    customColorDarkText     = '5725265'
    customColorDisabledText = '4277820'
    customColorLinkText     = '9537105'
    customColorEdge         = '2566179'
    customColorHotEdge      = '4342842'
    customColorDisabledEdge = '1842457'
    darkThemeName           = 'Lichen.xml'
}

Copy-Item $config "$config.lichen-backup" -Force

$doc = New-Object System.Xml.XmlDocument
$doc.PreserveWhitespace = $true
$doc.Load($config)

$gui = $doc.SelectSingleNode('/NotepadPlus/GUIConfigs')
$node = $gui.SelectSingleNode("GUIConfig[@name='DarkMode']")
if (-not $node) {
    $node = $doc.CreateElement('GUIConfig')
    $node.SetAttribute('name', 'DarkMode')
    $gui.AppendChild($node) | Out-Null
}
foreach ($key in $darkMode.Keys) {
    $node.SetAttribute($key, $darkMode[$key])
}

$settings = New-Object System.Xml.XmlWriterSettings
$settings.Encoding = New-Object System.Text.UTF8Encoding $false
$writer = [System.Xml.XmlWriter]::Create($config, $settings)
try { $doc.Save($writer) } finally { $writer.Close() }
Write-Host "Updated $config (backup: $config.lichen-backup)"
