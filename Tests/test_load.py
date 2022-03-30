import os

import pytest
import numpy as np

raw_path = os.path.abspath(os.path.join('.', __file__, '..', '..'))
if raw_path not in os.sys.path:
    os.sys.path.append(raw_path)

import bioxtasraw.RAWAPI as raw
import bioxtasraw.RAWSettings as RAWSettings
import bioxtasraw.SASM as SASM
import bioxtasraw.SECM as SECM


@pytest.fixture(scope="package")
def saxslab_settings():
    settings = raw.load_settings(os.path.join('.', 'data', 'settings_saxslab.cfg'))
    return settings

def test_load_settings_old(old_settings):
    settings = old_settings

    assert isinstance(settings, RAWSettings.RawGuiSettings)
    assert settings.get('NormAbsWater')
    assert settings.get('NormAbsWaterI0') == 0.0167
    assert settings.get('NormAbsWaterTemp') == '4'
    assert settings.get('NormAbsWaterConst') == 0.00071363632818
    assert settings.get('NormAbsWaterFile') == '/Users/jbh246/Box Sync/MacCHESS/BioSAXS Essentials/2016 (BE6)/raw_tutorial/Example_Data/test/A_water_A9_2_001_0000.dat'
    assert settings.get('NormAbsWaterEmptyFile') == '/Users/jbh246/Box Sync/MacCHESS/BioSAXS Essentials/2016 (BE6)/raw_tutorial/Example_Data/test/A_MT_A9_1_001_0000.dat'

    assert not settings.get('NormAbsCarbon')
    assert settings.get('NormAbsCarbonIgnoreBkg')
    assert settings.get('NormAbsCarbonFile') is None
    assert settings.get('NormAbsCarbonEmptyFile') is None
    assert settings.get('NormAbsCarbonSamEmptyFile') is None
    assert settings.get('NormAbsCarbonCalFile') is None
    assert settings.get('NormAbsCarbonThick') == 1.055
    assert settings.get('NormAbsCarbonSamThick') == 1.0
    assert settings.get('NormAbsCarbonUpstreamCtr') is None
    assert settings.get('NormAbsCarbonDownstreamCtr') is None
    assert settings.get('NormAbsCarbonConst') == 1.0
    assert settings.get('NormAbsCarbonSamEmptySASM') is None

    assert not settings.get('AutoBgSubtract')
    assert not settings.get('AutoBIFT')
    assert not settings.get('AutoAvg')
    assert not settings.get('AutoAvgRemovePlots')
    assert settings.get('AutoAvgRegExp') == ''
    assert settings.get('AutoAvgNameRegExp') == ''
    assert settings.get('AutoAvgNoOfFrames') == 1
    assert settings.get('AutoBgSubRegExp') == ''

    assert settings.get('DetectorFlipLR')
    assert not settings.get('DetectorFlipUD')
    assert not settings.get('UseHeaderForMask')
    assert not settings.get('UseHeaderForConfig')
    assert not settings.get('DetectorFlipped90')

    assert settings.get('DoSolidAngleCorrection')
    assert not settings.get('DoPolarizationCorrection')
    assert settings.get('PolarizationFactor') == 0
    assert settings.get('IntegrationMethod') == 'nosplit_csr'
    assert settings.get('AngularUnit') == 'q_A^-1'
    assert settings.get('ErrorModel') == 'poisson'
    assert not settings.get('UseImageForVariance')
    assert settings.get('AzimuthalIntegrator') is None

    assert not settings.get('DarkCorrEnabled')
    assert settings.get('DarkCorrFilename') is None
    assert settings.get('DarkCorrImage') is None
    assert not settings.get('NormFlatfieldEnabled')
    assert settings.get('NormFlatfieldFile') == 'None'
    assert settings.get('NormFlatfieldImage') is None

    assert settings.get('WaveLength') == 1.245
    assert settings.get('SampleDistance') == 1502.7
    assert settings.get('Detector') == 'Other'
    assert settings.get('DetectorPixelSizeX') == 172.0
    assert settings.get('DetectorPixelSizeY') == 172.0
    assert settings.get('DetectorTilt') == 0.0
    assert settings.get('DetectorTiltPlanRot') == 0.0
    assert settings.get('Xcenter') == -0.2
    assert settings.get('Ycenter') == 98.0

    assert settings.get('BinType') == 'Linear'
    assert settings.get('Binsize') == 1

    assert settings.get('StartPoint') == 17
    assert settings.get('EndPoint') == 5

    assert settings.get('BackgroundSASM') is None
    assert settings.get('DataSECM') is None
    assert settings.get('MaskDimension')[0] == 195
    assert settings.get('MaskDimension')[1] == 487
    assert settings.get('Masks')['TransparentBSMask'][0] is None
    assert settings.get('Masks')['TransparentBSMask'][1] is None

    assert settings.get('maxDmax') == 400.0
    assert settings.get('minDmax') == 10.0
    assert settings.get('DmaxPoints') == 10
    assert settings.get('maxAlpha') == 10000000000.0
    assert settings.get('minAlpha') == 150.0
    assert settings.get('AlphaPoints') == 16
    assert settings.get('PrPoints') == 50
    assert settings.get('mcRuns') == 300

    assert not settings.get('ZingerRemovalRadAvg')
    assert settings.get('ZingerRemovalRadAvgStd') == 4.0
    assert settings.get('ZingerRemovalRadAvgIter') == 5
    assert not settings.get('ZingerRemoval')
    assert settings.get('ZingerRemoveSTD') == 4
    assert settings.get('ZingerRemoveWinLen') == 10
    assert settings.get('ZingerRemoveIdx') == 10

    assert settings.get('ProcessedFilePath') == 'None'
    assert settings.get('AveragedFilePath') == 'None'
    assert settings.get('SubtractedFilePath') == 'None'
    assert settings.get('BiftFilePath') is None
    assert settings.get('GnomFilePath') is None
    assert not settings.get('AutoSaveOnImageFiles')
    assert not settings.get('AutoSaveOnAvgFiles')
    assert not settings.get('AutoSaveOnSub')
    assert not settings.get('AutoSaveOnBift')
    assert not settings.get('AutoSaveOnGnom')

    assert settings.get('ImageFormat') == 'Pilatus'
    assert settings.get('ImageHdrFormat') == 'G1, CHESS'
    assert settings.get('ImageHdrList')['Exposure_time'] == 1.0
    assert settings.get('FileHdrList')['I3'] == '1141'
    assert not settings.get('UseHeaderForCalib')

    #Not testing header bind list here

    assert len(settings.get('NormalizationList')) == 1
    assert settings.get('NormalizationList')[0][0] == '/'
    assert settings.get('NormalizationList')[0][1] == 'diode/259139'
    assert settings.get('EnableNormalization')

    assert settings.get('MetadataList') is None
    assert settings.get('EnableMetadata')

    assert len(settings.get('OnlineFilterList')) == 2
    assert settings.get('OnlineFilterList')[0][0] == 'Ignore'
    assert settings.get('OnlineFilterList')[0][1] == 'PIL3'
    assert settings.get('OnlineFilterList')[0][2] == 'Anywhere'
    assert settings.get('OnlineFilterList')[1][0] == 'Open only with'
    assert settings.get('OnlineFilterList')[1][1] == '.tiff'
    assert settings.get('OnlineFilterList')[1][2] == 'At end'
    assert settings.get('EnableOnlineFiltering')
    assert not settings.get('OnlineModeOnStartup')
    assert settings.get('OnlineStartupDir') is None
    assert settings.get('HdrLoadConfigDir') is None

    assert settings.get('MWStandardMW') == 14.3
    assert settings.get('MWStandardI0') == 0.04575
    assert settings.get('MWStandardConc') == 4.27
    assert settings.get('MWStandardFile') == 'S_A_lys2_A9_17_001_0000'

    assert settings.get('MWVcType') == 'Protein'
    assert settings.get('MWVcAProtein') == 1.0
    assert settings.get('MWVcBProtein') == 0.1231
    assert settings.get('MWVcARna') == 0.808
    assert settings.get('MWVcBRna') == 0.00934
    assert settings.get('MWVcCutoff') == 'Manual'
    assert settings.get('MWVcQmax') == 0.3

    assert settings.get('MWVpRho') == 0.00083
    assert settings.get('MWVpCutoff') == 'Default'
    assert settings.get('MWVpQmax') == 0.5

    assert settings.get('MWAbsRhoMprot') == 3.22*10**23
    assert settings.get('MWAbsRhoSolv') == 3.34*10**23
    assert settings.get('MWAbsNuBar') == 0.7425
    assert settings.get('MWAbsR0') == 2.8179*10**-13

    assert settings.get('secCalcThreshold') == 1.02
    assert settings.get('IBaselineMinIter') == 100
    assert settings.get('IBaselineMaxIter') == 2000

    assert settings.get('ManipItemCollapsed')
    assert not settings.get('DatHeaderOnTop')
    assert settings.get('PromptConfigLoad')

    assert settings.get('autoFindATSAS')

    assert settings.get('gnomExpertFile') == ''
    assert settings.get('gnomForceRminZero') == 'Y'
    assert settings.get('gnomForceRmaxZero') == 'Y'
    assert settings.get('gnomNPoints') == 101
    assert settings.get('gnomInitialAlpha') == 0.0
    assert settings.get('gnomAngularScale') == 1
    assert settings.get('gnomSystem') == 0
    assert settings.get('gnomFormFactor') == ''
    assert settings.get('gnomRadius56') == -1.0
    assert settings.get('gnomRmin') == -1.0
    assert settings.get('gnomFWHM') == -1.0
    assert settings.get('gnomAH') == -1.0
    assert settings.get('gnomLH') == -1.0
    assert settings.get('gnomAW') == -1.0
    assert settings.get('gnomLW') == -1.0
    assert settings.get('gnomSpot') == ''
    assert settings.get('gnomExpt') == 0
    assert not settings.get('gnomCut8Rg')

    assert settings.get('dammifMode') == 'Fast'
    assert settings.get('dammifSymmetry') == 'P1'
    assert settings.get('dammifUnit') == 'Unknown'
    assert not settings.get('dammifChained')
    assert settings.get('dammifConstant') == ''
    assert settings.get('dammifOmitSolvent')
    assert settings.get('dammifDummyRadius') -1.0
    assert settings.get('dammifSH') == -1
    assert settings.get('dammifPropToFit') == -1.0
    assert settings.get('dammifKnots') == -1
    assert settings.get('dammifCurveWeight') == 'e'
    assert settings.get('dammifRandomSeed') == ''
    assert settings.get('dammifMaxSteps') == -1
    assert settings.get('dammifMaxIters') == -1
    assert settings.get('dammifMaxStepSuccess') == -1
    assert settings.get('dammifMinStepSuccess') == -1
    assert settings.get('dammifTFactor') == -1.0
    assert settings.get('dammifRgPen') == -1.0
    assert settings.get('dammifCenPen') == -1.0
    assert settings.get('dammifLoosePen') == -1.0
    assert settings.get('dammifAnisPen') == -1.0
    assert settings.get('dammifMaxBeadCount') == -1
    assert settings.get('dammifReconstruct') == 15
    assert settings.get('dammifDamaver')
    assert not settings.get('dammifDamclust')
    assert settings.get('dammifRefine')
    assert settings.get('dammifProgram') == 'DAMMIF'
    assert settings.get('dammifExpectedShape') == 'u'

    assert settings.get('damminInitial') == 'S'
    assert settings.get('damminKnots') == 20
    assert settings.get('damminConstant') == 0
    assert settings.get('damminDiameter') == -1.0
    assert settings.get('damminPacking') == -1.0
    assert settings.get('damminCoordination') == -1.0
    assert settings.get('damminDisconPen') == -1.0
    assert settings.get('damminPeriphPen') == -1.0
    assert settings.get('damminCurveWeight') == '1'
    assert settings.get('damminAnealSched') == -1.0

    assert settings.get('weightCounter') == ''
    assert settings.get('weightByError')

    assert settings.get('errorWeight')
    assert settings.get('normalizedResiduals')

    assert settings.get('denssVoxel') == 5.0
    assert settings.get('denssOversampling') == 3.0
    assert settings.get('denssNElectrons') == '10000'
    assert settings.get('denssSteps') == 'None'
    assert not settings.get('denssLimitDmax')
    assert settings.get('denssLimitDmaxStep') == '[502]'
    assert settings.get('denssRecenter')
    assert settings.get('denssRecenterStep') == '[501, 1001, 1501, 2001, 2501, 3001, 3501, 4001, 4501, 5001, 5501, 6001, 6501, 7001, 7501, 8001]'
    assert settings.get('denssPositivity')
    assert settings.get('denssExtrapolate')
    assert settings.get('denssShrinkwrap')
    assert settings.get('denssShrinkwrapSigmaStart') == 'None'
    assert settings.get('denssShrinkwrapSigmaEnd') == 'None'
    assert settings.get('denssShrinkwrapSigmaDecay') == 0.99
    assert settings.get('denssShrinkwrapThresFrac') == 0.2
    assert settings.get('denssShrinkwrapIter') == 20
    assert settings.get('denssShrinkwrapMinStep') == 'None'
    assert settings.get('denssConnected')
    assert settings.get('denssConnectivitySteps') == '[500]'
    assert settings.get('denssChiEndFrac') == 0.001
    assert settings.get('denssAverage')
    assert settings.get('denssReconstruct') == 20
    assert not settings.get('denssCutOut')
    assert not settings.get('denssWriteXplor')
    assert settings.get('denssMode') == 'Slow'
    assert settings.get('denssRecenterMode') == 'com'
    assert settings.get('denssNCS') == 0
    assert settings.get('denssNCSSteps') == '[3000,5000,7000,9000]'
    assert settings.get('denssNCSAxis') == 1
    assert settings.get('denssRefine')

def test_load_settings_new():
    settings = raw.load_settings(os.path.join('.', 'data', 'settings_new.cfg'))

    assert isinstance(settings, RAWSettings.RawGuiSettings)
    assert not settings.get('NormAbsWater')
    assert settings.get('NormAbsWaterI0') == 0.01632
    assert settings.get('NormAbsWaterTemp') == '25'
    assert settings.get('NormAbsWaterConst') == 1.0
    assert settings.get('NormAbsWaterFile') == 'None'
    assert settings.get('NormAbsWaterEmptyFile') == 'None'

    assert not settings.get('NormAbsCarbon')
    assert settings.get('NormAbsCarbonIgnoreBkg')
    assert settings.get('NormAbsCarbonFile') == 'None'
    assert settings.get('NormAbsCarbonEmptyFile') == 'None'
    assert settings.get('NormAbsCarbonSamEmptyFile') == 'None'
    assert settings.get('NormAbsCarbonCalFile') == 'None'
    assert settings.get('NormAbsCarbonThick') == 1.055
    assert settings.get('NormAbsCarbonSamThick') == 1.0
    assert settings.get('NormAbsCarbonUpstreamCtr') == 'Beam_current\n'
    assert settings.get('NormAbsCarbonDownstreamCtr') == 'Beam_current\n'
    assert settings.get('NormAbsCarbonConst') == 1.0
    assert settings.get('NormAbsCarbonSamEmptySASM') is None

    assert not settings.get('AutoBgSubtract')
    assert not settings.get('AutoBIFT')
    assert not settings.get('AutoAvg')
    assert not settings.get('AutoAvgRemovePlots')
    assert settings.get('AutoAvgRegExp') == ''
    assert settings.get('AutoAvgNameRegExp') == ''
    assert settings.get('AutoAvgNoOfFrames') == 1
    assert settings.get('AutoBgSubRegExp') == ''

    assert not settings.get('DetectorFlipLR')
    assert not settings.get('DetectorFlipUD')
    assert not settings.get('UseHeaderForMask')
    assert not settings.get('UseHeaderForConfig')
    assert not settings.get('DetectorFlipped90')

    assert settings.get('DoSolidAngleCorrection')
    assert not settings.get('DoPolarizationCorrection')
    assert settings.get('PolarizationFactor') == 0
    assert settings.get('IntegrationMethod') == 'nosplit_csr'
    assert settings.get('AngularUnit') == 'q_A^-1'
    assert settings.get('ErrorModel') == 'poisson'
    assert not settings.get('UseImageForVariance')
    assert settings.get('AzimuthalIntegrator') is None

    assert not settings.get('DarkCorrEnabled')
    assert settings.get('DarkCorrFilename') == ''
    assert settings.get('DarkCorrImage') is None
    assert not settings.get('NormFlatfieldEnabled')
    assert settings.get('NormFlatfieldFile') == ''
    assert settings.get('NormFlatfieldImage') is None

    assert settings.get('WaveLength') == 1.0332016536100022
    assert settings.get('SampleDistance') == 3695.710292891765
    assert settings.get('Detector') == 'pilatus_1m'
    assert settings.get('DetectorPixelSizeX') == 172.0
    assert settings.get('DetectorPixelSizeY') == 172.0
    assert settings.get('DetectorTilt') == 0.667099158537498
    assert settings.get('DetectorTiltPlanRot') == -131.04642951948335
    assert settings.get('Xcenter') == 915.8803153878777
    assert settings.get('Ycenter') == 878.0032650871369

    assert settings.get('BinType') == 'Linear'
    assert settings.get('Binsize') == 1

    assert settings.get('StartPoint') == 13
    assert settings.get('EndPoint') == 0

    assert settings.get('BackgroundSASM') is None
    assert settings.get('DataSECM') is None
    assert settings.get('MaskDimension')[0] == 1043
    assert settings.get('MaskDimension')[1] == 981
    assert settings.get('Masks')['TransparentBSMask'][0] is None
    assert settings.get('Masks')['TransparentBSMask'][1] is None

    assert settings.get('maxDmax') == 400.0
    assert settings.get('minDmax') == 10.0
    assert settings.get('DmaxPoints') == 10
    assert settings.get('maxAlpha') == 10000000000.0
    assert settings.get('minAlpha') == 150.0
    assert settings.get('AlphaPoints') == 16
    assert settings.get('PrPoints') == 100
    assert settings.get('mcRuns') == 300

    assert not settings.get('ZingerRemovalRadAvg')
    assert settings.get('ZingerRemovalRadAvgStd') == 5.0
    assert settings.get('ZingerRemovalRadAvgIter') == 5
    assert not settings.get('ZingerRemoval')
    assert settings.get('ZingerRemoveSTD') == 4
    assert settings.get('ZingerRemoveWinLen') == 10
    assert settings.get('ZingerRemoveIdx') == 10

    assert settings.get('ProcessedFilePath') == 'None'
    assert settings.get('AveragedFilePath') == 'None'
    assert settings.get('SubtractedFilePath') == 'None'
    assert settings.get('BiftFilePath') == 'None'
    assert settings.get('GnomFilePath') == 'None'
    assert not settings.get('AutoSaveOnImageFiles')
    assert not settings.get('AutoSaveOnAvgFiles')
    assert not settings.get('AutoSaveOnSub')
    assert not settings.get('AutoSaveOnBift')
    assert not settings.get('AutoSaveOnGnom')

    assert settings.get('ImageFormat') == 'Pilatus'
    assert settings.get('ImageHdrFormat') == 'BioCAT, APS'
    assert settings.get('ImageHdrList')['Exposure_time'] == '0.5000000 s'
    assert settings.get('FileHdrList')['I0'] == '5905.0'
    assert not settings.get('UseHeaderForCalib')

    #Not testing header bind list here

    assert len(settings.get('NormalizationList')) == 1
    assert settings.get('NormalizationList')[0][0] == '/'
    assert settings.get('NormalizationList')[0][1] == 'I1'
    assert settings.get('EnableNormalization')

    assert len(settings.get('MetadataList')) == 0
    assert settings.get('EnableMetadata')

    assert len(settings.get('OnlineFilterList')) == 2
    assert settings.get('OnlineFilterList')[0][0] == 'Ignore'
    assert settings.get('OnlineFilterList')[0][1] == 'PIL3'
    assert settings.get('OnlineFilterList')[0][2] == 'Anywhere'
    assert settings.get('OnlineFilterList')[1][0] == 'Open only with'
    assert settings.get('OnlineFilterList')[1][1] == '.tiff'
    assert settings.get('OnlineFilterList')[1][2] == 'At end'
    assert not settings.get('EnableOnlineFiltering')
    assert not settings.get('OnlineModeOnStartup')
    assert settings.get('OnlineStartupDir') == 'None'
    assert settings.get('HdrLoadConfigDir') == 'None'

    assert settings.get('MWStandardMW') == 0.0
    assert settings.get('MWStandardI0') == 0.0
    assert settings.get('MWStandardConc') == 0.0
    assert settings.get('MWStandardFile') == ''

    assert settings.get('MWVcType') == 'Protein'
    assert settings.get('MWVcAProtein') == 1.0
    assert settings.get('MWVcBProtein') == 0.1231
    assert settings.get('MWVcARna') == 0.808
    assert settings.get('MWVcBRna') == 0.00934
    assert settings.get('MWVcCutoff') == 'Default'
    assert settings.get('MWVcQmax') == 0.5

    assert settings.get('MWVpRho') == 0.00083
    assert settings.get('MWVpCutoff') == 'Default'
    assert settings.get('MWVpQmax') == 0.5

    assert settings.get('MWAbsRhoMprot') == 3.22*10**23
    assert settings.get('MWAbsRhoSolv') == 3.34*10**23
    assert settings.get('MWAbsNuBar') == 0.7425
    assert settings.get('MWAbsR0') == 2.8179*10**-13

    assert settings.get('secCalcThreshold') == 1.02
    assert settings.get('IBaselineMinIter') == 100
    assert settings.get('IBaselineMaxIter') == 2000

    assert not settings.get('ManipItemCollapsed')
    assert not settings.get('DatHeaderOnTop')
    assert settings.get('PromptConfigLoad')

    assert settings.get('autoFindATSAS')

    assert settings.get('gnomExpertFile') == ''
    assert settings.get('gnomForceRminZero') == 'Y'
    assert settings.get('gnomForceRmaxZero') == 'Y'
    assert settings.get('gnomNPoints') == 0
    assert settings.get('gnomInitialAlpha') == 0.0
    assert settings.get('gnomAngularScale') == 1
    assert settings.get('gnomSystem') == 0
    assert settings.get('gnomFormFactor') == ''
    assert settings.get('gnomRadius56') == -1.0
    assert settings.get('gnomRmin') == -1.0
    assert settings.get('gnomFWHM') == -1.0
    assert settings.get('gnomAH') == -1.0
    assert settings.get('gnomLH') == -1.0
    assert settings.get('gnomAW') == -1.0
    assert settings.get('gnomLW') == -1.0
    assert settings.get('gnomSpot') == ''
    assert settings.get('gnomExpt') == 0
    assert not settings.get('gnomCut8Rg')

    assert settings.get('dammifMode') == 'Slow'
    assert settings.get('dammifSymmetry') == 'P1'
    assert settings.get('dammifUnit') == 'Unknown'
    assert not settings.get('dammifChained')
    assert settings.get('dammifConstant') == ''
    assert settings.get('dammifOmitSolvent')
    assert settings.get('dammifDummyRadius') -1.0
    assert settings.get('dammifSH') == -1
    assert settings.get('dammifPropToFit') == -1.0
    assert settings.get('dammifKnots') == -1
    assert settings.get('dammifCurveWeight') == 'e'
    assert settings.get('dammifRandomSeed') == ''
    assert settings.get('dammifMaxSteps') == -1
    assert settings.get('dammifMaxIters') == -1
    assert settings.get('dammifMaxStepSuccess') == -1
    assert settings.get('dammifMinStepSuccess') == -1
    assert settings.get('dammifTFactor') == -1.0
    assert settings.get('dammifRgPen') == -1.0
    assert settings.get('dammifCenPen') == -1.0
    assert settings.get('dammifLoosePen') == -1.0
    assert settings.get('dammifAnisPen') == -1.0
    assert settings.get('dammifMaxBeadCount') == -1
    assert settings.get('dammifReconstruct') == 15
    assert settings.get('dammifDamaver')
    assert not settings.get('dammifDamclust')
    assert settings.get('dammifRefine')
    assert settings.get('dammifProgram') == 'DAMMIF'
    assert settings.get('dammifExpectedShape') == 'u'

    assert settings.get('damminInitial') == 'S'
    assert settings.get('damminKnots') == 20
    assert settings.get('damminConstant') == 0
    assert settings.get('damminDiameter') == -1.0
    assert settings.get('damminPacking') == -1.0
    assert settings.get('damminCoordination') == -1.0
    assert settings.get('damminDisconPen') == -1.0
    assert settings.get('damminPeriphPen') == -1.0
    assert settings.get('damminCurveWeight') == '1'
    assert settings.get('damminAnealSched') == -1.0

    assert settings.get('weightCounter') == ''
    assert settings.get('weightByError')

    assert settings.get('errorWeight')
    assert settings.get('normalizedResiduals')

    assert settings.get('denssVoxel') == 5.0
    assert settings.get('denssOversampling') == 3.0
    assert settings.get('denssNElectrons') == ''
    assert settings.get('denssSteps') == 10000
    assert not settings.get('denssLimitDmax')
    assert settings.get('denssLimitDmaxStep') == '[500]'
    assert settings.get('denssRecenter')
    assert settings.get('denssRecenterStep') == '[1001, 1501, 2001, 2501, 3001, 3501, 4001, 4501, 5001, 5501, 6001, 6501, 7001, 7501, 8001]'
    assert settings.get('denssPositivity')
    assert settings.get('denssExtrapolate')
    assert settings.get('denssShrinkwrap')
    assert settings.get('denssShrinkwrapSigmaStart') == 3.0
    assert settings.get('denssShrinkwrapSigmaEnd') == 1.5
    assert settings.get('denssShrinkwrapSigmaDecay') == 0.99
    assert settings.get('denssShrinkwrapThresFrac') == 0.2
    assert settings.get('denssShrinkwrapIter') == 20
    assert settings.get('denssShrinkwrapMinStep') == 5000
    assert settings.get('denssConnected')
    assert settings.get('denssConnectivitySteps') == '[7500]'
    assert settings.get('denssChiEndFrac') == 0.001
    assert settings.get('denssAverage')
    assert settings.get('denssReconstruct') == 20
    assert not settings.get('denssCutOut')
    assert settings.get('denssWriteXplor')
    assert settings.get('denssMode') == 'Slow'
    assert settings.get('denssRecenterMode') == 'com'
    assert settings.get('denssNCS') == 0
    assert settings.get('denssNCSSteps') == '[3000,5000,7000,9000]'
    assert settings.get('denssNCSAxis') == 1
    assert settings.get('denssRefine')

def test_load_settings_saxslab():
    settings = raw.load_settings(os.path.join('.', 'data', 'settings_saxslab.cfg'))

    assert isinstance(settings, RAWSettings.RawGuiSettings)
    assert not settings.get('NormAbsWater')
    assert settings.get('NormAbsWaterI0') == 0.01632
    assert settings.get('NormAbsWaterTemp') == '25'
    assert settings.get('NormAbsWaterConst') == 1.0
    assert settings.get('NormAbsWaterFile') == 'None'
    assert settings.get('NormAbsWaterEmptyFile') == 'None'

    assert not settings.get('NormAbsCarbon')
    assert settings.get('NormAbsCarbonIgnoreBkg')
    assert settings.get('NormAbsCarbonFile') == 'None'
    assert settings.get('NormAbsCarbonEmptyFile') == 'None'
    assert settings.get('NormAbsCarbonSamEmptyFile') == 'None'
    assert settings.get('NormAbsCarbonCalFile') == 'None'
    assert settings.get('NormAbsCarbonThick') == 1.055
    assert settings.get('NormAbsCarbonSamThick') == 1.0
    assert settings.get('NormAbsCarbonUpstreamCtr') == ''
    assert settings.get('NormAbsCarbonDownstreamCtr') == ''
    assert settings.get('NormAbsCarbonConst') == 1.0
    assert settings.get('NormAbsCarbonSamEmptySASM') is None

    assert not settings.get('AutoBgSubtract')
    assert not settings.get('AutoBIFT')
    assert not settings.get('AutoAvg')
    assert not settings.get('AutoAvgRemovePlots')
    assert settings.get('AutoAvgRegExp') == ''
    assert settings.get('AutoAvgNameRegExp') == ''
    assert settings.get('AutoAvgNoOfFrames') == 1
    assert settings.get('AutoBgSubRegExp') == ''

    assert not settings.get('DetectorFlipLR')
    assert not settings.get('DetectorFlipUD')
    assert settings.get('UseHeaderForMask')
    assert not settings.get('UseHeaderForConfig')
    assert settings.get('DetectorFlipped90')

    assert settings.get('DoSolidAngleCorrection')
    assert not settings.get('DoPolarizationCorrection')
    assert settings.get('PolarizationFactor') == 0
    assert settings.get('IntegrationMethod') == 'nosplit_csr'
    assert settings.get('AngularUnit') == 'q_A^-1'
    assert settings.get('ErrorModel') == 'poisson'
    assert not settings.get('UseImageForVariance')
    assert settings.get('AzimuthalIntegrator') is None

    assert not settings.get('DarkCorrEnabled')
    assert settings.get('DarkCorrFilename') is None
    assert settings.get('DarkCorrImage') is None
    assert not settings.get('NormFlatfieldEnabled')
    assert settings.get('NormFlatfieldFile') == 'None'
    assert settings.get('NormFlatfieldImage') is None

    assert settings.get('WaveLength') == 1.0
    assert settings.get('SampleDistance') == 1000.0
    assert settings.get('Detector') == 'Other'
    assert settings.get('DetectorPixelSizeX') == 70.5
    assert settings.get('DetectorPixelSizeY') == 70.5
    assert settings.get('DetectorTilt') == 0.0
    assert settings.get('DetectorTiltPlanRot') == 0.0
    assert settings.get('Xcenter') == 512.0
    assert settings.get('Ycenter') == 512.0

    assert settings.get('BinType') == 'Linear'
    assert settings.get('Binsize') == 1

    assert settings.get('StartPoint') == 0
    assert settings.get('EndPoint') == 0

    assert settings.get('BackgroundSASM') is None
    assert settings.get('DataSECM') is None
    assert settings.get('MaskDimension') == 1024
    assert settings.get('Masks')['TransparentBSMask'][0] is None
    assert settings.get('Masks')['TransparentBSMask'][1] is None

    assert settings.get('maxDmax') == 400.0
    assert settings.get('minDmax') == 10.0
    assert settings.get('DmaxPoints') == 10
    assert settings.get('maxAlpha') == 10000000000.0
    assert settings.get('minAlpha') == 150.0
    assert settings.get('AlphaPoints') == 16
    assert settings.get('PrPoints') == 100
    assert settings.get('mcRuns') == 300

    assert not settings.get('ZingerRemovalRadAvg')
    assert settings.get('ZingerRemovalRadAvgStd') == 4.0
    assert settings.get('ZingerRemovalRadAvgIter') == 5
    assert not settings.get('ZingerRemoval')
    assert settings.get('ZingerRemoveSTD') == 4
    assert settings.get('ZingerRemoveWinLen') == 10
    assert settings.get('ZingerRemoveIdx') == 10

    assert settings.get('ProcessedFilePath') == 'None'
    assert settings.get('AveragedFilePath') == 'None'
    assert settings.get('SubtractedFilePath') == 'None'
    assert settings.get('BiftFilePath') == 'None'
    assert settings.get('GnomFilePath') == 'None'
    assert not settings.get('AutoSaveOnImageFiles')
    assert not settings.get('AutoSaveOnAvgFiles')
    assert not settings.get('AutoSaveOnSub')
    assert not settings.get('AutoSaveOnBift')
    assert not settings.get('AutoSaveOnGnom')

    assert settings.get('ImageFormat') == 'SAXSLab300'
    assert settings.get('ImageHdrFormat') == 'None'
    assert settings.get('ImageHdrList')['detx'] == 349.996875
    assert settings.get('FileHdrList') is None
    assert settings.get('UseHeaderForCalib')

    assert settings.get('HeaderBindList')['Wavelength'][0] == "WaveLength"
    assert settings.get('HeaderBindList')['Wavelength'][1][0] == "wavelength"
    assert settings.get('HeaderBindList')['Wavelength'][1][1] == "imghdr"

    assert len(settings.get('NormalizationList')) == 0
    assert not settings.get('EnableNormalization')

    assert len(settings.get('MetadataList')) == 0
    assert settings.get('EnableMetadata')

    assert len(settings.get('OnlineFilterList')) == 0
    assert not settings.get('EnableOnlineFiltering')
    assert not settings.get('OnlineModeOnStartup')
    assert settings.get('OnlineStartupDir') == 'None'
    assert settings.get('HdrLoadConfigDir') == 'None'

    assert settings.get('MWStandardMW') == 0.0
    assert settings.get('MWStandardI0') == 0.0
    assert settings.get('MWStandardConc') == 0.0
    assert settings.get('MWStandardFile') == ''

    assert settings.get('MWVcType') == 'Protein'
    assert settings.get('MWVcAProtein') == 1.0
    assert settings.get('MWVcBProtein') == 0.1231
    assert settings.get('MWVcARna') == 0.808
    assert settings.get('MWVcBRna') == 0.00934
    assert settings.get('MWVcCutoff') == 'Manual'
    assert settings.get('MWVcQmax') == 0.3

    assert settings.get('MWVpRho') == 0.00083
    assert settings.get('MWVpCutoff') == 'Default'
    assert settings.get('MWVpQmax') == 0.5

    assert settings.get('MWAbsRhoMprot') == 3.22*10**23
    assert settings.get('MWAbsRhoSolv') == 3.34*10**23
    assert settings.get('MWAbsNuBar') == 0.7425
    assert settings.get('MWAbsR0') == 2.8179*10**-13

    assert settings.get('secCalcThreshold') == 1.02
    assert settings.get('IBaselineMinIter') == 100
    assert settings.get('IBaselineMaxIter') == 2000

    assert not settings.get('ManipItemCollapsed')
    assert not settings.get('DatHeaderOnTop')
    assert settings.get('PromptConfigLoad')

    assert settings.get('autoFindATSAS')

    assert settings.get('gnomExpertFile') == ''
    assert settings.get('gnomForceRminZero') == 'Y'
    assert settings.get('gnomForceRmaxZero') == 'Y'
    assert settings.get('gnomNPoints') == 0
    assert settings.get('gnomInitialAlpha') == 0.0
    assert settings.get('gnomAngularScale') == 1
    assert settings.get('gnomSystem') == 0
    assert settings.get('gnomFormFactor') == ''
    assert settings.get('gnomRadius56') == -1.0
    assert settings.get('gnomRmin') == -1.0
    assert settings.get('gnomFWHM') == -1.0
    assert settings.get('gnomAH') == -1.0
    assert settings.get('gnomLH') == -1.0
    assert settings.get('gnomAW') == -1.0
    assert settings.get('gnomLW') == -1.0
    assert settings.get('gnomSpot') == ''
    assert settings.get('gnomExpt') == 0
    assert not settings.get('gnomCut8Rg')

    assert settings.get('dammifMode') == 'Slow'
    assert settings.get('dammifSymmetry') == 'P1'
    assert settings.get('dammifUnit') == 'Unknown'
    assert not settings.get('dammifChained')
    assert settings.get('dammifConstant') == ''
    assert settings.get('dammifOmitSolvent')
    assert settings.get('dammifDummyRadius') -1.0
    assert settings.get('dammifSH') == -1
    assert settings.get('dammifPropToFit') == -1.0
    assert settings.get('dammifKnots') == -1
    assert settings.get('dammifCurveWeight') == 'e'
    assert settings.get('dammifRandomSeed') == ''
    assert settings.get('dammifMaxSteps') == -1
    assert settings.get('dammifMaxIters') == -1
    assert settings.get('dammifMaxStepSuccess') == -1
    assert settings.get('dammifMinStepSuccess') == -1
    assert settings.get('dammifTFactor') == -1.0
    assert settings.get('dammifRgPen') == -1.0
    assert settings.get('dammifCenPen') == -1.0
    assert settings.get('dammifLoosePen') == -1.0
    assert settings.get('dammifAnisPen') == -1.0
    assert settings.get('dammifMaxBeadCount') == -1
    assert settings.get('dammifReconstruct') == 15
    assert settings.get('dammifDamaver')
    assert not settings.get('dammifDamclust')
    assert settings.get('dammifRefine')
    assert settings.get('dammifProgram') == 'DAMMIF'
    assert settings.get('dammifExpectedShape') == 'u'

    assert settings.get('damminInitial') == 'S'
    assert settings.get('damminKnots') == 20
    assert settings.get('damminConstant') == 0
    assert settings.get('damminDiameter') == -1.0
    assert settings.get('damminPacking') == -1.0
    assert settings.get('damminCoordination') == -1.0
    assert settings.get('damminDisconPen') == -1.0
    assert settings.get('damminPeriphPen') == -1.0
    assert settings.get('damminCurveWeight') == '1'
    assert settings.get('damminAnealSched') == -1.0

    assert settings.get('weightCounter') == ''
    assert settings.get('weightByError')

    assert settings.get('errorWeight')
    assert settings.get('normalizedResiduals')

    assert settings.get('denssVoxel') == 5.0
    assert settings.get('denssOversampling') == 3.0
    assert settings.get('denssNElectrons') == ''
    assert settings.get('denssSteps') == 10000
    assert not settings.get('denssLimitDmax')
    assert settings.get('denssLimitDmaxStep') == '[500]'
    assert settings.get('denssRecenter')
    assert settings.get('denssRecenterStep') == '[1001, 1501, 2001, 2501, 3001, 3501, 4001, 4501, 5001, 5501, 6001, 6501, 7001, 7501, 8001]'
    assert settings.get('denssPositivity')
    assert settings.get('denssExtrapolate')
    assert settings.get('denssShrinkwrap')
    assert settings.get('denssShrinkwrapSigmaStart') == 3.0
    assert settings.get('denssShrinkwrapSigmaEnd') == 1.5
    assert settings.get('denssShrinkwrapSigmaDecay') == 0.99
    assert settings.get('denssShrinkwrapThresFrac') == 0.2
    assert settings.get('denssShrinkwrapIter') == 20
    assert settings.get('denssShrinkwrapMinStep') == 5000
    assert settings.get('denssConnected')
    assert settings.get('denssConnectivitySteps') == '[7500]'
    assert settings.get('denssChiEndFrac') == 0.001
    assert settings.get('denssAverage')
    assert settings.get('denssReconstruct') == 20
    assert not settings.get('denssCutOut')
    assert settings.get('denssWriteXplor')
    assert settings.get('denssMode') == 'Slow'
    assert settings.get('denssRecenterMode') == 'com'
    assert settings.get('denssNCS') == 0
    assert settings.get('denssNCSSteps') == '[3000,5000,7000,9000]'
    assert settings.get('denssNCSAxis') == 1
    assert settings.get('denssRefine')

def test_load_profile_without_settings():
    filenames = [os.path.join('.', 'data', 'glucose_isomerase.dat')]
    profiles = raw.load_profiles(filenames)

    assert len(profiles) == 1
    assert isinstance(profiles[0], SASM.SASM)

    sasm = profiles[0]

    assert len(sasm.getQ()) == 474
    assert len(sasm.getI()) == 474
    assert len(sasm.getErr()) == 474
    assert sasm.getQ()[0] == 1.00967275E-02
    assert sasm.getQ()[-1] == 2.82996847E-01
    assert sasm.getI()[0] == 5.85325362E-02
    assert sasm.getI()[-1] == 6.45540600E-04
    assert sasm.getErr()[0] == 1.59855527E-03
    assert sasm.getErr()[-1] == 5.14117602E-04
    assert sasm.getI().sum() == 3.7220912003
    assert sasm.getQErr() is None

    params = sasm.getAllParameters()

    assert params['analysis']['guinier']['Rg'] == "33.607769051354296"
    assert params['raw_version'] == '2.0.0'
    assert params['imageHeader']['Gain_setting'] == "mid gain (vrf = -0.200)"
    assert params['config_file'] == "/Users/jesse/Desktop/Tutorial_Data/standards_data/SAXS.cfg"
    assert 'calibration_params' in params

def test_load_profile_with_settings(old_settings):
    settings = old_settings
    filenames = [os.path.join('.', 'data', 'glucose_isomerase.dat')]
    profiles = raw.load_profiles(filenames, settings)

    assert len(profiles) == 1
    assert isinstance(profiles[0], SASM.SASM)

    sasm = profiles[0]

    assert len(sasm.getQ()) == 474
    assert len(sasm.getI()) == 474
    assert len(sasm.getErr()) == 474
    assert sasm.getQ()[0] == 1.00967275E-02
    assert sasm.getQ()[-1] == 2.82996847E-01
    assert sasm.getI()[0] == 5.85325362E-02
    assert sasm.getI()[-1] == 6.45540600E-04
    assert sasm.getErr()[0] == 1.59855527E-03
    assert sasm.getErr()[-1] == 5.14117602E-04
    assert sasm.getI().sum() == 3.7220912003
    assert sasm.getQErr() is None

    params = sasm.getAllParameters()

    assert params['analysis']['guinier']['Rg'] == "33.607769051354296"
    assert params['raw_version'] == '2.0.0'
    assert params['imageHeader']['Gain_setting'] == "mid gain (vrf = -0.200)"
    assert params['config_file'] == "/Users/jesse/Desktop/Tutorial_Data/standards_data/SAXS.cfg"
    assert 'calibration_params' in params

def test_load_sans_profile():
    filenames = [os.path.join('.', 'data', 'sans_data.dat')]
    profiles = raw.load_profiles(filenames)

    assert len(profiles) == 1
    assert isinstance(profiles[0], SASM.SASM)

    sasm = profiles[0]

    assert len(sasm.getQ()) == 117
    assert len(sasm.getI()) == 117
    assert len(sasm.getErr()) == 117
    assert len(sasm.getQErr()) == 117
    assert sasm.getQ()[0] == 6.85263400E-03
    assert sasm.getQ()[-1] == 7.83923000E-01
    assert sasm.getI()[0] == 7.47717600E-01
    assert sasm.getI()[-1] == 9.83200300E-01
    assert sasm.getErr()[0] == 1.28509700E-01
    assert sasm.getErr()[-1] == 1.73155300E-03
    assert sasm.getI().sum() == 115.9909959
    assert sasm.getQErr()[0] == 2.09011000E-03
    assert sasm.getQErr()[-1] == 4.22697600E-02
    assert sasm.getQErr().sum() == 1.141910318

def test_load_gnom_ift():
    filenames = [os.path.join('.', 'data', 'glucose_isomerase.out')]

    ifts = raw.load_ifts(filenames)

    assert len(ifts) == 1
    assert isinstance(ifts[0], SASM.IFTM)

    iftm = ifts[0]

    assert len(iftm.q_orig) == 474
    assert len(iftm.i_orig) == 474
    assert len(iftm.err_orig) == 474
    assert len(iftm.i_fit) == 474
    assert len(iftm.q_extrap) == 492
    assert len(iftm.i_extrap) == 492
    assert len(iftm.r) == 174
    assert len(iftm.p) == 174
    assert len(iftm.err) == 174

    assert iftm.q_orig[0] == 0.100967E-01
    assert iftm.q_orig[-1] == 0.282997E+00
    assert iftm.i_orig[0] == 0.585325E-01
    assert iftm.i_orig[-1] == 0.645541E-03
    assert iftm.err_orig[0] == 0.159856E-02
    assert iftm.err_orig[-1] == 0.514118E-03
    assert iftm.i_orig.sum() == 3.7220912315
    assert iftm.i_fit[0] == 0.589055E-01
    assert iftm.i_fit[-1] == 0.489008E-04
    assert iftm.i_fit.sum() == 3.7299845326999996
    assert iftm.q_extrap[0] == 0
    assert iftm.q_extrap[-1] == 0.282997E+00
    assert iftm.i_extrap[0] == 0.611794E-01
    assert iftm.i_extrap[-1] == 0.489008E-04
    assert iftm.i_extrap.sum() == 4.8185919326999995

    assert iftm.r[0] == 0
    assert iftm.r[20] == 0.1168E+02
    assert iftm.r[-1] == 0.1010E+03
    assert iftm.p[0] == 0.0000E+00
    assert iftm.p[20] == 0.2181E-04
    assert iftm.p[-1] == 0.0000E+00
    assert iftm.err[0] == 0.0000E+00
    assert iftm.err[20] == 0.3170E-06
    assert iftm.err[-1] == 0.0000E+00
    assert iftm.p.sum() == 0.00833920043

    assert iftm.getParameter('rg') == 0.3336E+02
    assert iftm.getParameter('rger') == 0.1073E+00
    assert iftm.getParameter('TE') == 0.9708
    assert iftm.getParameter('smooth') == 0.164


def test_load_bift_ift():
    filenames = [os.path.join('.', 'data', 'glucose_isomerase.ift')]

    ifts = raw.load_ifts(filenames)

    assert len(ifts) == 1
    assert isinstance(ifts[0], SASM.IFTM)

    iftm = ifts[0]

    assert len(iftm.q_orig) == 474
    assert len(iftm.i_orig) == 474
    assert len(iftm.err_orig) == 474
    assert len(iftm.i_fit) == 474
    assert len(iftm.q_extrap) == 475
    assert len(iftm.i_extrap) == 475
    assert len(iftm.r) == 50
    assert len(iftm.p) == 50
    assert len(iftm.err) == 50

    assert iftm.q_orig[0] == 1.00967275E-02
    assert iftm.q_orig[-1] == 2.82996847E-01
    assert iftm.i_orig[0] == 5.85325362E-02
    assert iftm.i_orig[-1] == 6.45540600E-04
    assert iftm.err_orig[0] == 1.59855527E-03
    assert iftm.err_orig[-1] == 5.14117602E-04
    assert iftm.i_orig.sum() == 3.7220912003
    assert iftm.i_fit[0] == 5.88215180E-02
    assert iftm.i_fit[-1] == 1.09619395E-04
    assert iftm.i_fit.sum() == 3.7274259507984997
    assert iftm.q_extrap[0] == 0
    assert iftm.q_extrap[-1] == 2.82996847E-01
    assert iftm.i_extrap[0] == 6.10690886E-02
    assert iftm.i_extrap[-1] == 1.09619395E-04
    assert iftm.i_extrap.sum() == 3.7884950393984997

    assert iftm.r[0] == 0
    assert iftm.r[20] == 4.13355642E+01
    assert iftm.r[-1] == 1.01272132E+02
    assert iftm.p[0] == 0.0000E+00
    assert iftm.p[20] == 1.07277826E-04
    assert iftm.p[-1] == 0.0000E+00
    assert iftm.err[0] == 0.0000E+00
    assert iftm.err[20] == 1.60803653E-07
    assert iftm.err[-1] == 6.12786738E-07
    assert iftm.p.sum() == 0.002351352283335

    assert iftm.getParameter('rg') == 33.19046563192041
    assert iftm.getParameter('rger') == 0.1335668087605545
    assert iftm.getParameter('dmaxer') == 7.736527037387454

def test_load_series_old_from_dats():
    filenames = [os.path.join('.', 'data', 'series_old_dats.sec')]

    series_list = raw.load_series(filenames)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 324
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/sec_data/sec_sample_2/BSA_001_0000.dat'
    assert secm.total_i[0] == 10.507738068398014
    assert secm.total_i[-1] == 10.473601708833439
    assert secm.total_i.sum() == 3732.5782999682183
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 18
    assert secm.buffer_range[0][1] == 53
    assert secm.sample_range[0][0] == 186
    assert secm.sample_range[0][1] == 204
    assert secm.baseline_start_range[0] == 0
    assert secm.baseline_start_range[1] == 10
    assert secm.baseline_end_range[0] == 313
    assert secm.baseline_end_range[1] == 323
    assert secm.rg_list[200] == 28.162821930667974
    assert secm.rger_list[200] == 0.048597694707159224
    assert secm.i0_list[200] == 139.43907985696447
    assert secm.i0er_list[200] == 0.053375241246074026
    assert secm.vpmw_list[200] == 70.20715754037127
    assert secm.vcmw_list[200] == 66.19982252918054
    assert secm.vcmwer_list[200] == 8.136327336653839

    assert secm.series_type == ''
    assert secm._scale_factor == 1.0
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 324
    assert len(secm.use_subtracted_sasm) == 324
    assert secm.total_i_sub.sum() == 331.3353154360302
    assert secm.baseline_type == 'Linear'
    assert len(secm.baseline_subtracted_sasm_list) == 324
    assert len(secm.use_baseline_subtracted_sasm) == 324
    assert secm.total_i_bcsub.sum() == 336.10343643715805

def test_load_series_old_from_images():
    filenames = [os.path.join('.', 'data', 'series_old_images.sec')]

    series_list = raw.load_series(filenames)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 20
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/standards_data/GI2_A9_19_001_0000.tiff'
    assert secm.total_i[0] == 0.00849019951198231
    assert secm.total_i[-1] == 0.006450808839648731
    assert secm.total_i.sum() == 0.14957343176362306
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 10
    assert secm.buffer_range[0][1] == 19
    assert secm.sample_range[0][0] == 0
    assert secm.sample_range[0][1] == 9
    assert secm.baseline_start_range[0] == -1
    assert secm.baseline_start_range[1] == -1
    assert secm.baseline_end_range[0] == -1
    assert secm.baseline_end_range[1] == -1
    assert secm.rg_list[5] == 33.683172944318386
    assert secm.rger_list[5] == 0.14381270762042558
    assert secm.i0_list[5] == 0.060902075649185775
    assert secm.i0er_list[5] == 6.252846257453396e-05
    assert secm.vpmw_list[5] == 175.69101996458616
    assert secm.vcmw_list[5] == 149.26121735553096
    assert secm.vcmwer_list[5] == 12.217250810044417

    assert secm.series_type == ''
    assert secm._scale_factor == 1.0
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 20
    assert len(secm.use_subtracted_sasm) == 20
    assert secm.total_i_sub.sum() == 0.02117810710880871
    assert secm.baseline_type == ''
    assert len(secm.baseline_subtracted_sasm_list) == 0
    assert len(secm.use_baseline_subtracted_sasm) == 0
    assert secm.total_i_bcsub.sum() == 0

def test_load_series_new_from_dats():
    filenames = [os.path.join('.', 'data', 'series_new_dats.hdf5')]

    series_list = raw.load_series(filenames)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 324
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/sec_data/sec_sample_2/BSA_001_0000.dat'
    assert secm.total_i[0] == 11.558511875237816
    assert secm.total_i[-1] == 11.520961879716785
    assert secm.total_i.sum() == 4105.8361299650405
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 18
    assert secm.buffer_range[0][1] == 53
    assert secm.sample_range[0][0] == 186
    assert secm.sample_range[0][1] == 204
    assert secm.baseline_start_range[0] == 0
    assert secm.baseline_start_range[1] == 10
    assert secm.baseline_end_range[0] == 313
    assert secm.baseline_end_range[1] == 323
    assert secm.rg_list[200] == 28.162821930667974
    assert secm.rger_list[200] == 0.048597694707159224
    assert secm.i0_list[200] == 139.43907985696447
    assert secm.i0er_list[200] == 0.053375241246074026
    assert secm.vpmw_list[200] == 70.20715754037127
    assert secm.vcmw_list[200] == 66.19982252918054
    assert secm.vcmwer_list[200] == 8.136327336653839

    assert secm.series_type == 'SEC'
    assert secm._scale_factor == 1.1
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 324
    assert len(secm.use_subtracted_sasm) == 324
    assert secm.use_subtracted_sasm[200]
    assert not secm.use_subtracted_sasm[0]
    assert secm.total_i_sub.sum() == 364.4688469796332
    assert secm.baseline_type == 'Linear'
    assert len(secm.baseline_subtracted_sasm_list) == 324
    assert len(secm.use_baseline_subtracted_sasm) == 324
    assert secm.total_i_bcsub.sum() == 369.7137800808739

def test_load_series_new_from_images():
    filenames = [os.path.join('.', 'data', 'series_new_images.hdf5')]

    series_list = raw.load_series(filenames)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 20
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/standards_data/GI2_A9_19_001_0000.tiff'
    assert secm.total_i[0] == 0.008572792727392729
    assert secm.total_i[-1] == 0.00652181489858442
    assert secm.total_i.sum() == 0.15115388467535384
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 10
    assert secm.buffer_range[0][1] == 19
    assert secm.sample_range[0][0] == 0
    assert secm.sample_range[0][1] == 9
    assert secm.baseline_start_range[0] == -1
    assert secm.baseline_start_range[1] == -1
    assert secm.baseline_end_range[0] == -1
    assert secm.baseline_end_range[1] == -1
    assert secm.rg_list[5] == 33.41144081141521
    assert secm.rger_list[5] ==  0.14643097551510054
    assert secm.i0_list[5] == 0.0612436524713722
    assert secm.i0er_list[5] == 6.448212328651976e-05
    assert secm.vpmw_list[5] == 170.75822723417173
    assert secm.vcmw_list[5] == 146.34110536370417
    assert secm.vcmwer_list[5] == 12.097152779216445

    assert secm.series_type == 'SEC'
    assert secm._scale_factor == 1.0
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 20
    assert len(secm.use_subtracted_sasm) == 20
    assert secm.total_i_sub.sum() == 0.021304107772845166
    assert secm.baseline_type == ''
    assert len(secm.baseline_subtracted_sasm_list) == 0
    assert len(secm.use_baseline_subtracted_sasm) == 0
    assert secm.total_i_bcsub.sum() == 0

def test_load_series_old_from_dats_with_settings(old_settings):
    filenames = [os.path.join('.', 'data', 'series_old_dats.sec')]

    series_list = raw.load_series(filenames, old_settings)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 324
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/sec_data/sec_sample_2/BSA_001_0000.dat'
    assert secm.total_i[0] == 10.507738068398014
    assert secm.total_i[-1] == 10.473601708833439
    assert secm.total_i.sum() == 3732.5782999682183
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 18
    assert secm.buffer_range[0][1] == 53
    assert secm.sample_range[0][0] == 186
    assert secm.sample_range[0][1] == 204
    assert secm.baseline_start_range[0] == 0
    assert secm.baseline_start_range[1] == 10
    assert secm.baseline_end_range[0] == 313
    assert secm.baseline_end_range[1] == 323
    assert secm.rg_list[200] == 28.162821930667974
    assert secm.rger_list[200] == 0.048597694707159224
    assert secm.i0_list[200] == 139.43907985696447
    assert secm.i0er_list[200] == 0.053375241246074026
    assert secm.vpmw_list[200] == 70.20715754037127
    assert secm.vcmw_list[200] == 66.19982252918054
    assert secm.vcmwer_list[200] == 8.136327336653839

    assert secm.series_type == ''
    assert secm._scale_factor == 1.0
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 324
    assert len(secm.use_subtracted_sasm) == 324
    assert secm.total_i_sub.sum() == 331.3353154360302
    assert secm.baseline_type == 'Linear'
    assert len(secm.baseline_subtracted_sasm_list) == 324
    assert len(secm.use_baseline_subtracted_sasm) == 324
    assert secm.total_i_bcsub.sum() == 336.10343643715805

def test_load_series_old_from_images_with_settings(old_settings):
    filenames = [os.path.join('.', 'data', 'series_old_images.sec')]

    series_list = raw.load_series(filenames, old_settings)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 20
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/standards_data/GI2_A9_19_001_0000.tiff'
    assert secm.total_i[0] == 0.00849019951198231
    assert secm.total_i[-1] == 0.006450808839648731
    assert secm.total_i.sum() == 0.14957343176362306
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 10
    assert secm.buffer_range[0][1] == 19
    assert secm.sample_range[0][0] == 0
    assert secm.sample_range[0][1] == 9
    assert secm.baseline_start_range[0] == -1
    assert secm.baseline_start_range[1] == -1
    assert secm.baseline_end_range[0] == -1
    assert secm.baseline_end_range[1] == -1
    assert secm.rg_list[5] == 33.683172944318386
    assert secm.rger_list[5] == 0.14381270762042558
    assert secm.i0_list[5] == 0.060902075649185775
    assert secm.i0er_list[5] == 6.252846257453396e-05
    assert secm.vpmw_list[5] == 175.69101996458616
    assert secm.vcmw_list[5] == 149.26121735553096
    assert secm.vcmwer_list[5] == 12.217250810044417

    assert secm.series_type == ''
    assert secm._scale_factor == 1.0
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 20
    assert len(secm.use_subtracted_sasm) == 20
    assert secm.total_i_sub.sum() == 0.02117810710880871
    assert secm.baseline_type == ''
    assert len(secm.baseline_subtracted_sasm_list) == 0
    assert len(secm.use_baseline_subtracted_sasm) == 0
    assert secm.total_i_bcsub.sum() == 0

def test_load_series_new_from_dats_with_settings(old_settings):
    filenames = [os.path.join('.', 'data', 'series_new_dats.hdf5')]

    series_list = raw.load_series(filenames, old_settings)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 324
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/sec_data/sec_sample_2/BSA_001_0000.dat'
    assert secm.total_i[0] == 11.558511875237816
    assert secm.total_i[-1] == 11.520961879716785
    assert secm.total_i.sum() == 4105.8361299650405
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 18
    assert secm.buffer_range[0][1] == 53
    assert secm.sample_range[0][0] == 186
    assert secm.sample_range[0][1] == 204
    assert secm.baseline_start_range[0] == 0
    assert secm.baseline_start_range[1] == 10
    assert secm.baseline_end_range[0] == 313
    assert secm.baseline_end_range[1] == 323
    assert secm.rg_list[200] == 28.162821930667974
    assert secm.rger_list[200] == 0.048597694707159224
    assert secm.i0_list[200] == 139.43907985696447
    assert secm.i0er_list[200] == 0.053375241246074026
    assert secm.vpmw_list[200] == 70.20715754037127
    assert secm.vcmw_list[200] == 66.19982252918054
    assert secm.vcmwer_list[200] == 8.136327336653839

    assert secm.series_type == 'SEC'
    assert secm._scale_factor == 1.1
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 324
    assert len(secm.use_subtracted_sasm) == 324
    assert secm.total_i_sub.sum() == 364.4688469796332
    assert secm.baseline_type == 'Linear'
    assert len(secm.baseline_subtracted_sasm_list) == 324
    assert len(secm.use_baseline_subtracted_sasm) == 324
    assert secm.total_i_bcsub.sum() == 369.7137800808739

def test_load_series_new_from_images_with_settings(old_settings):
    filenames = [os.path.join('.', 'data', 'series_new_images.hdf5')]

    series_list = raw.load_series(filenames, old_settings)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 20
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/standards_data/GI2_A9_19_001_0000.tiff'
    assert secm.total_i[0] == 0.008572792727392729
    assert secm.total_i[-1] == 0.00652181489858442
    assert secm.total_i.sum() == 0.15115388467535384
    assert secm.window_size == 5
    assert secm.buffer_range[0][0] == 10
    assert secm.buffer_range[0][1] == 19
    assert secm.sample_range[0][0] == 0
    assert secm.sample_range[0][1] == 9
    assert secm.baseline_start_range[0] == -1
    assert secm.baseline_start_range[1] == -1
    assert secm.baseline_end_range[0] == -1
    assert secm.baseline_end_range[1] == -1
    assert secm.rg_list[5] == 33.41144081141521
    assert secm.rger_list[5] ==  0.14643097551510054
    assert secm.i0_list[5] == 0.0612436524713722
    assert secm.i0er_list[5] == 6.448212328651976e-05
    assert secm.vpmw_list[5] == 170.75822723417173
    assert secm.vcmw_list[5] == 146.34110536370417
    assert secm.vcmwer_list[5] == 12.097152779216445

    assert secm.series_type == 'SEC'
    assert secm._scale_factor == 1.0
    assert secm._offset_value == 0.0
    assert secm._frame_scale_factor == 1.0
    assert secm.mol_type == 'Protein'
    assert secm.mol_density == 0.00083
    assert not secm.already_subtracted
    assert isinstance(secm.average_buffer_sasm, SASM.SASM)
    assert len(secm.subtracted_sasm_list) == 20
    assert len(secm.use_subtracted_sasm) == 20
    assert secm.total_i_sub.sum() == 0.021304107772845166
    assert secm.baseline_type == ''
    assert len(secm.baseline_subtracted_sasm_list) == 0
    assert len(secm.use_baseline_subtracted_sasm) == 0
    assert secm.total_i_bcsub.sum() == 0

def test_load_series_sasbdb_keywords():
    filenames = [os.path.join('.', 'data', 'series_with_sasbdb_keywords.hdf5')]

    series_list = raw.load_series(filenames)

    assert len(series_list) == 1
    assert isinstance(series_list[0], SECM.SECM)

    secm = series_list[0]

    assert len(secm._file_list) == 10
    assert secm._file_list[0] == '/Users/jesse/Desktop/Tutorial_Data/standards_data/GI2_A9_19_001_0000.tiff'
    assert secm.total_i[0] == 0.008572792727392729
    assert secm.total_i[-1] == 0.008598722084516956

def test_load_images(old_settings):
    filenames = [os.path.join('.', 'data', 'GI2_A9_19_001_0000.tiff')]

    img_list, img_hdr_list = raw.load_images(filenames, old_settings)

    assert len(img_list) == 1
    assert len(img_hdr_list) == 1
    assert isinstance(img_list[0], np.ndarray)
    assert isinstance(img_hdr_list[0], dict)

    img = img_list[0]
    img_hdr = img_hdr_list[0]

    assert img.shape[0] == 195
    assert img.shape[1] == 487
    assert img.sum() == 594964
    assert img.max() == 39
    assert img.min() == -2
    assert img[50, 50] == 21

    assert img_hdr['Pixel_size'] == '172e-6 m x 172e-6 m'
    assert img_hdr['Exposure_time'] == '1.0000000 s'

def test_load_images_saxslab(saxslab_settings):
    filenames = [os.path.join('.', 'data', 'saxslab_image.tiff')]

    img_list, img_hdr_list = raw.load_images(filenames, saxslab_settings)

    assert len(img_list) == 1
    assert len(img_hdr_list) == 1
    assert isinstance(img_list[0], np.ndarray)
    assert isinstance(img_hdr_list[0], dict)

    img = img_list[0]
    img_hdr = img_hdr_list[0]

    assert img.shape[0] == 487
    assert img.shape[1] == 619
    assert img.sum() == 34737747
    assert img.max() == 230504
    assert img.min() == -2
    assert img[50, 50] == 1

    assert img_hdr['beam_x'] == 359.1
    assert img_hdr['det_exposure_time'] == 999.0
    assert img_hdr['saxsconf_wavelength'] == 1.5418

def test_load_and_integrate_images(old_settings):
    filenames = [os.path.join('.', 'data', 'GI2_A9_19_001_0000.tiff')]

    profile_list, img_list = raw.load_and_integrate_images(filenames, old_settings)

    assert len(img_list) == 1
    assert isinstance(img_list[0], np.ndarray)
    assert len(profile_list) == 1
    assert isinstance(profile_list[0], SASM.SASM)

    img = img_list[0]

    assert img.shape[0] == 195
    assert img.shape[1] == 487
    assert img.sum() == 594964
    assert img.max() == 39
    assert img.min() == -2
    assert img[50, 50] == 21

    sasm = profile_list[0]

    assert len(sasm.getQ()) == 474
    assert len(sasm.getI()) == 474
    assert len(sasm.getErr()) == 474
    assert sasm.getQ()[0] == 0.010096727470341287
    assert sasm.getQ()[-1] == 0.28299684709728007
    assert np.isclose(sasm.getI()[0], 0.10278217)
    assert np.isclose(sasm.getI()[-1], 0.022769544)
    assert np.isclose(sasm.getErr()[0], 0.0041513327)
    assert np.isclose(sasm.getErr()[-1], 0.0011515054, rtol=2e-3)
    assert np.isclose(sasm.getI().sum(), 14.921439)

    params = sasm.getAllParameters()

    assert params['imageHeader']['Gain_setting'] == "mid gain (vrf = -0.200)"
    assert 'calibration_params' in params

def test_load_and_integrate_images_saxslab(saxslab_settings):
    filenames = [os.path.join('.', 'data', 'saxslab_image.tiff')]

    profile_list, img_list = raw.load_and_integrate_images(filenames, saxslab_settings)

    assert len(img_list) == 1

    img = img_list[0]

    assert img.shape[0] == 487
    assert img.shape[1] == 619
    assert img.sum() == 34737747
    assert img.max() == 230504
    assert img.min() == -2
    assert img[50, 50] == 1

    sasm = profile_list[0]

    assert len(sasm.getQ()) == 447
    assert len(sasm.getI()) == 447
    assert len(sasm.getErr()) == 447
    assert sasm.getQ()[0] == 0.0007122250118961234
    assert sasm.getQ()[-1] == 0.6360169356232382
    assert sasm.getI()[0] == 0.0
    assert np.isclose(sasm.getI()[-1], -1.0374458)
    assert sasm.getErr()[0] == 0.0
    assert np.isclose(sasm.getErr()[-1], 0.59896964)
    assert np.isclose(sasm.getI().sum(), 483950.22)

    params = sasm.getAllParameters()

    assert params['imageHeader']['beam_x'] == 359.1
    assert params['imageHeader']['det_exposure_time'] == 999.0
    assert params['imageHeader']['saxsconf_wavelength'] == 1.5418
    assert 'calibration_params' in params

def test_profile_to_series():
    filenames = [os.path.join('.', 'data', 'series_dats',
        'BSA_001_{:04d}.dat'.format(i)) for i in range(10)]

    profiles = raw.load_profiles(filenames)

    series = raw.profiles_to_series(profiles)

    test_filenames = [os.path.split(fname)[1] for fname in filenames]

    assert isinstance(series, SECM.SECM)
    assert series._file_list == test_filenames
    assert series.total_i.sum() == 105.06363296992504

def test_profile_to_series_with_settings(old_settings):
    filenames = [os.path.join('.', 'data', 'series_dats',
        'BSA_001_{:04d}.dat'.format(i)) for i in range(10)]

    profiles = raw.load_profiles(filenames, old_settings)

    series = raw.profiles_to_series(profiles, old_settings)

    test_filenames = [os.path.split(fname)[1] for fname in filenames]

    assert isinstance(series, SECM.SECM)
    assert series._file_list == test_filenames
    assert series.total_i.sum() == 105.06363296992504

def test_make_profile():
    filenames = [os.path.join('.', 'data', 'glucose_isomerase.dat')]
    profile = raw.load_profiles(filenames)[0]

    new_profile = raw.make_profile(profile.getQ(), profile.getI(),
        profile.getErr(), profile.getParameter('filename'))

    assert all(new_profile.getQ() == profile.getQ())
    assert all(new_profile.getI() == profile.getI())
    assert all(new_profile.getErr() == profile.getErr())

def test_load_crysol_int():
    filenames = [os.path.join('.', 'data', 'crysol.int')]

    profile = raw.load_profiles(filenames)[0]

    assert profile.getQ()[0] == 0
    assert profile.getQ()[-1] == 0.5
    assert profile.getI()[0] == 503777000
    assert profile.getI()[-1] == 181594.0
    assert profile.getErr()[0] == 22444.977166395158
    assert profile.getErr()[-1] == 426.1384751462839
    assert len(profile.getQ()) == 51
    assert len(profile.getI()) == 51
    assert len(profile.getErr()) == 51
    assert profile.getI().sum() == 2522896411.0

def test_load_crysol_fit():
    filenames = [os.path.join('.', 'data', 'crysol.fit')]

    profiles = raw.load_profiles(filenames)
    data = profiles[0]
    fit = profiles[1]

    assert data.getQ()[0] == 0
    assert data.getQ()[-1] == 0.240054
    assert data.getI()[0] == 0
    assert data.getI()[-1] == -0.00456588
    assert data.getErr()[0] == 0
    assert data.getErr()[-1] == 0.00352755
    assert len(data.getQ()) == 409
    assert len(data.getI()) == 409
    assert len(data.getErr()) == 409
    assert data.getI().sum() == 150.841626209

    assert fit.getQ()[0] == 0
    assert fit.getQ()[-1] == 0.240054
    assert fit.getI()[0] == 2.18238
    assert fit.getI()[-1] == 0.00136142
    assert fit.getErr()[0] == 0.0
    assert fit.getErr()[-1] == 0.00352755
    assert len(fit.getQ()) == 409
    assert len(fit.getI()) == 409
    assert len(fit.getErr()) == 409
    assert fit.getI().sum() == 160.75817242999997

def test_load_foxs_dat():
    filenames = [os.path.join('.', 'data', 'foxs.dat')]

    profile = raw.load_profiles(filenames)[0]

    assert profile.getQ()[0] == 0
    assert profile.getQ()[-1] == 0.5
    assert profile.getI()[0] == 91131976
    assert profile.getI()[-1] == 92309.8828125
    assert profile.getErr()[0] == 19137.71484375
    assert profile.getErr()[-1] == 12486.7578125
    assert len(profile.getQ()) == 501
    assert len(profile.getI()) == 501
    assert len(profile.getErr()) == 501
    assert profile.getI().sum() == 4620558481.1484375

def test_load_foxs_fit():
    filenames = [os.path.join('.', 'data', 'foxs.fit')]

    profiles = raw.load_profiles(filenames)
    data = profiles[0]
    fit = profiles[1]

    assert data.getQ()[0] == 0.00972485
    assert data.getQ()[-1] == 0.24005422
    assert data.getI()[0] == 2.19981909
    assert data.getI()[-1] == -0.00456588
    assert data.getErr()[0] == 0.02850627
    assert data.getErr()[-1] == 0.00352755
    assert len(data.getQ()) == 404
    assert len(data.getI()) == 404
    assert len(data.getErr()) == 404
    assert data.getI().sum() == 150.84163809

    assert fit.getQ()[0] == 0.00972485
    assert fit.getQ()[-1] == 0.24005422
    assert fit.getI()[0] == 2.10481598
    assert fit.getI()[-1] == 0.00187786
    assert fit.getErr()[0] == 0.02850627
    assert fit.getErr()[-1] == 0.00352755
    assert len(fit.getQ()) == 404
    assert len(fit.getI()) == 404
    assert len(fit.getErr()) == 404
    assert fit.getI().sum() == 149.89277113

def test_load_dammif_fir():
    filenames = [os.path.join('.', 'data', 'dammif.fir')]

    profiles = raw.load_profiles(filenames)
    data = profiles[0]
    fit = profiles[1]

    assert data.getQ()[0] == 0.0100967
    assert data.getQ()[-1] == 0.237417
    assert data.getI()[0] == 0.0585325
    assert data.getI()[-1] == -6.91805e-5
    assert data.getErr()[0] == 0.00159856
    assert data.getErr()[-1] == 0.000326748
    assert len(data.getQ()) == 395
    assert len(data.getI()) == 395
    assert len(data.getErr()) == 395
    assert data.getI().sum() == 3.7167194811999997

    assert fit.getQ()[0] == 0.0100967
    assert fit.getQ()[-1] == 0.237417
    assert fit.getI()[0] == 0.0592096
    assert fit.getI()[-1] == 7.68452e-5
    assert fit.getErr()[0] == 0.00159856
    assert fit.getErr()[-1] == 0.000326748
    assert len(fit.getQ()) == 395
    assert len(fit.getI()) == 395
    assert len(fit.getErr()) == 395
    assert fit.getI().sum() == 3.7354253277000002

def test_load_dammif_fit():
    filenames = [os.path.join('.', 'data', 'dammif.fit')]

    profiles = raw.load_profiles(filenames)
    fit1 = profiles[0]
    fit2 = profiles[1]

    assert fit1.getQ()[0] == 0.0005609
    assert fit1.getQ()[-1] == 0.2374
    assert fit1.getI()[0] == 0.0612
    assert fit1.getI()[-1] == 1.18e-7
    assert len(fit1.getQ()) == 412
    assert len(fit1.getI()) == 412
    assert len(fit1.getErr()) == 412
    assert fit1.getI().sum() == 4.741580228799999

    assert fit2.getQ()[0] == 0.0005609
    assert fit2.getQ()[-1] == 0.2374
    assert fit2.getI()[0] == 0.06119
    assert fit2.getI()[-1] == 1.945e-5
    assert len(fit2.getQ()) == 412
    assert len(fit2.getI()) == 412
    assert len(fit2.getErr()) == 412
    assert fit2.getI().sum() == 4.7433277

def test_load_waxsis_dat():
    filenames = [os.path.join('.', 'data', 'waxsis.dat')]

    profile = raw.load_profiles(filenames)[0]

    assert profile.getQ()[0] == 0
    assert profile.getQ()[-1] == 1
    assert profile.getI()[0] == 89896000
    assert profile.getI()[-1] == 67326.6
    assert profile.getErr()[0] == 873004
    assert profile.getErr()[-1] == 1394.74
    assert len(profile.getQ()) == 101
    assert len(profile.getI()) == 101
    assert len(profile.getErr()) == 101
    assert profile.getI().sum() == 491682748.7000001

def test_load_csv_dat():
    filenames = [os.path.join('.', 'data', 'csv.dat')]

    profile = raw.load_profiles(filenames)[0]

    assert len(profile.getQ()) == 474
    assert len(profile.getI()) == 474
    assert len(profile.getErr()) == 474
    assert profile.getQ()[0] == 1.00967275E-02
    assert profile.getQ()[-1] == 2.82996847E-01
    assert profile.getI()[0] == 5.85325362E-02
    assert profile.getI()[-1] == 6.45540600E-04
    assert profile.getErr()[0] == 1.59855527E-03
    assert profile.getErr()[-1] == 5.14117602E-04
    assert profile.getI().sum() == 3.7220912003

def test_load_counter_values(old_settings):
    filenames = [os.path.join('.', 'data', 'GI2_A9_19_001_0000.tiff')]

    counters = raw.load_counter_values(filenames, old_settings)[0]

    assert float(counters['I1']) == 92616
    assert float(counters['diode']) == 39391
    assert float(counters['Seconds']) == 1
    assert float(counters['I3']) == 1149
    assert float(counters['Time']) == 5.9604645e-6
    assert float(counters['Epoch']) == 2
    assert float(counters['hep']) == 0
    assert float(counters['gdoor']) == 1187

def test_integrate_image(old_settings):
    filenames = [os.path.join('.', 'data', 'GI2_A9_19_001_0000.tiff')]

    counters = raw.load_counter_values(filenames, old_settings)[0]

    img, img_hdr = raw.load_images(filenames, old_settings)
    img = img[0]
    img_hdr = img_hdr[0]

    profile = raw.integrate_image(img, old_settings, 'test_image', img_hdr,
        counters, filenames[0])

    profile_list, img_list = raw.load_and_integrate_images(filenames, old_settings)

    assert all(profile.getQ() == profile_list[0].getQ())
    assert all(profile.getI() == profile_list[0].getI())
    assert all(profile.getErr() == profile_list[0].getErr())

