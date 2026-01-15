import { useKBWizardForm } from "./useKBWizardForm";
import { BasicInfoStep } from "./BasicInfoStep";
import { SourceTypeStep } from "./SourceTypeStep";
import { ConfigurationStep } from "./ConfigurationStep";
import { ReviewStep } from "./ReviewStep";

interface WizardContentProps {
  readonly form: ReturnType<typeof useKBWizardForm>;
}

export function WizardContent({ form }: WizardContentProps) {
  const { step } = form;

  if (step === "basic") {
    return (
      <BasicInfoStep
        name={form.name}
        setName={form.setName}
        kbId={form.kbId}
        setKbId={form.setKbId}
        description={form.description}
        setDescription={form.setDescription}
      />
    );
  }
  if (step === "source") {
    return (
      <SourceTypeStep
        sourceType={form.sourceType}
        setSourceType={form.setSourceType}
      />
    );
  }
  if (step === "config") {
    return (
      <ConfigurationStep
        sourceType={form.sourceType}
        urls={form.urls}
        setUrls={form.setUrls}
        sitemapUrl={form.sitemapUrl}
        setSitemapUrl={form.setSitemapUrl}
        urlPrefix={form.urlPrefix}
        setUrlPrefix={form.setUrlPrefix}
        videoUrls={form.videoUrls}
        setVideoUrls={form.setVideoUrls}
        pdfLocalPaths={form.pdfLocalPaths}
        setPdfLocalPaths={form.setPdfLocalPaths}
        pdfUrls={form.pdfUrls}
        setPdfUrls={form.setPdfUrls}
        pdfFolderPath={form.pdfFolderPath}
        setPdfFolderPath={form.setPdfFolderPath}
        markdownFolderPath={form.markdownFolderPath}
        setMarkdownFolderPath={form.setMarkdownFolderPath}
      />
    );
  }
  return (
    <ReviewStep
      name={form.name}
      kbId={form.kbId}
      description={form.description}
      sourceType={form.sourceType}
      urls={form.urls}
      sitemapUrl={form.sitemapUrl}
      videoUrls={form.videoUrls}
      pdfLocalPaths={form.pdfLocalPaths}
      pdfUrls={form.pdfUrls}
      pdfFolderPath={form.pdfFolderPath}
      markdownFolderPath={form.markdownFolderPath}
    />
  );
}
