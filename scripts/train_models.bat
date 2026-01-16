@echo off
REM ============================================================================
REM HealthGuard ML Model Training Commands (Windows)
REM ============================================================================
REM GPU: NVIDIA RTX 4050 (6GB VRAM)
REM All models configured for CUDA with TF32 enabled
REM
REM Training includes:
REM   - Batch-level logging (loss, gradients, metrics)
REM   - Per-epoch validation (5-10 metrics)
REM   - Final evaluation (10+ metrics)
REM   - GPU memory monitoring
REM   - Training history saved to JSON
REM ============================================================================

cd /d "%~dp0\.."

echo ==============================================
echo HealthGuard ML Training Commands
echo ==============================================
echo GPU: RTX 4050 (6GB VRAM)
echo.

REM Check CUDA
echo Checking CUDA availability...
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0)}' if torch.cuda.is_available() else 'CPU only')"
echo.

if "%1"=="" goto menu
if "%1"=="1" goto additive
if "%1"=="1+" goto additive_plus
if "%1"=="2" goto nova
if "%1"=="3" goto procedure
if "%1"=="all" goto all
goto menu

:menu
echo ==============================================
echo Select model to train:
echo ==============================================
echo.
echo   1. Additive Risk Scorer  (~5 min, 42 additives)
echo   1+ FoodScore+ Scorer     (~15 min, 344 additives, DistilBERT)
echo   2. NOVA Classifier       (~30-60 min)
echo   3. Procedure Encoder     (~2-5 hrs)
echo.
echo   all - Train all models in sequence
echo.
echo Usage: train_models.bat [1^|1+^|2^|3^|all]
echo.
echo ==============================================
echo Manual Commands:
echo ==============================================
echo.
echo # 1. Additive Scorer (original, 42 additives):
echo python -m ml.additive_scorer.train --epochs 200 --batch-size 16
echo.
echo # 1+. FoodScore+ (enhanced, 344 additives):
echo python -m ml.additive_scorer_plus.train --epochs 50 --batch-size 16
echo.
echo # 2. NOVA Classifier:
echo python -m ml.nova_classifier.train --epochs 20 --batch-size 64
echo.
echo # 3. Procedure Encoder:
echo python -m ml.procedure_encoder.train --epochs 3 --batch-size 32
echo.
echo # Quick test with smaller data:
echo python -m ml.nova_classifier.train --epochs 5 --sample-size 50000
echo.
goto end

:additive
echo ==============================================
echo Training: Additive Risk Scorer (Original)
echo ==============================================
python -m ml.additive_scorer.train --epochs 200 --batch-size 16
goto end

:additive_plus
echo ==============================================
echo Training: FoodScore+ Enhanced Scorer
echo ==============================================
python -m ml.additive_scorer_plus.train --epochs 50 --batch-size 16
goto end

:nova
echo ==============================================
echo Training: NOVA Classifier
echo ==============================================
python -m ml.nova_classifier.train --epochs 20 --batch-size 64
goto end

:procedure
echo ==============================================
echo Training: Procedure Encoder
echo ==============================================
python -m ml.procedure_encoder.train --epochs 3 --batch-size 32
goto end

:all
echo ==============================================
echo Training ALL Models
echo ==============================================
echo.
echo Step 1/3: Additive Risk Scorer
python -m ml.additive_scorer.train --epochs 200 --batch-size 8
echo.
echo Step 2/3: NOVA Classifier
python -m ml.nova_classifier.train --epochs 20 --batch-size 64
echo.
echo Step 3/3: Procedure Encoder
python -m ml.procedure_encoder.train --epochs 3 --batch-size 32
echo.
echo ==============================================
echo ALL TRAINING COMPLETE
echo ==============================================
goto end

:end
echo.
echo Done.
