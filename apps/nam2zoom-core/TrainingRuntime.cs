namespace Nam2ZoomDesktop;

public sealed class TrainingRuntime(AppPaths paths, BackendService backend,
    Func<string, IEnumerable<string>, Action<string>, CancellationToken, Task<ProcessResult>>? execute = null)
{
    public bool HasPreference => File.Exists(paths.TrainingPreference);
    private Task<ProcessResult> Run(string python, IEnumerable<string> args, Action<string> report, CancellationToken token) =>
        execute is null ? backend.ExecuteAsync(python, args, report, token) : execute(python, args, report, token);

    public async Task SelectAsync(bool cuda, Action<string> report, CancellationToken token)
    {
        if (cuda && !OperatingSystem.IsWindows())
            throw new PlatformNotSupportedException("CUDA setup is available on Windows only.");
        Directory.CreateDirectory(Path.GetDirectoryName(paths.TrainingPreference)!);
        if (cuda) {
            if (paths.TrainingDevice == "cuda") {
                await VerifyAsync(report, token);
                return;
            }
            // Keep the shipped CPU runtime intact. Inherit its NAM and audio packages,
            // but install CUDA torch locally in a separate user-owned environment.
            var venv = Path.GetDirectoryName(Path.GetDirectoryName(paths.CudaTrainer)!)!;
            var created = await Run(paths.DefaultTrainer,
                ["-c", "import venv,sysconfig,pathlib,sys; venv.EnvBuilder(with_pip=True,system_site_packages=True).create(sys.argv[1]); p=pathlib.Path(sys.argv[1])/'Lib'/'site-packages'/'nam2zoom-base.pth'; p.write_text(sysconfig.get_path('purelib')+'\\n')", venv], report, token);
            created.RequireSuccess();
            report("Downloading NVIDIA CUDA training packages (several GB). No driver is installed.");
            var installed = await Run(paths.CudaTrainer,
                ["-m", "pip", "--isolated", "install", "--only-binary=:all:", "--ignore-installed", "--no-deps",
                 "torch==2.11.0+cu128", "--index-url", "https://download.pytorch.org/whl/cu128"], report, token);
            installed.RequireSuccess();
            var verified = await Run(paths.CudaTrainer, ["-c",
                "import nam.cli, torch; assert torch.cuda.is_available(), 'CUDA is unavailable. Check your NVIDIA driver; CPU training remains available.'; x=torch.ones(1, device='cuda'); print('Training GPU: '+torch.cuda.get_device_name(0)); print('CUDA tensor check: '+str(x.cpu().item()))"], report, token);
            if (verified.Exit != 0)
                throw new InvalidOperationException("CUDA verification failed. Check your NVIDIA driver, then retry Training device or choose CPU. The previous choice is unchanged.\n" + verified.Output);
        }
        token.ThrowIfCancellationRequested();
        // Activate only after installation and a real GPU allocation succeed.
        var temporary = paths.TrainingPreference + ".tmp";
        await File.WriteAllTextAsync(temporary, cuda ? "cuda" : "cpu", token);
        File.Move(temporary, paths.TrainingPreference, true);
        report(cuda ? "NVIDIA GPU training enabled." : "CPU training selected.");
    }

    public async Task VerifyAsync(Action<string> report, CancellationToken token)
    {
        var code = paths.TrainingDevice == "cuda"
            ? "import torch; assert torch.cuda.is_available(), 'Selected NVIDIA GPU is unavailable. Open Training device to retry setup or select CPU.'; x=torch.ones(1,device='cuda'); print('Training GPU: '+torch.cuda.get_device_name(0))"
            : "print('Training device: CPU')";
        var result = await Run(paths.Trainer, ["-c", code], report, token);
        if (result.Exit != 0) throw new InvalidOperationException("Training runtime verification failed. Open Training device to select CPU or retry NVIDIA setup.\n" + result.Output);
    }
}
