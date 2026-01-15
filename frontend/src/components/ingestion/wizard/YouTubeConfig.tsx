import { ArrayInput } from "./ArrayInput";

interface YouTubeConfigProps {
  readonly videoUrls: string[];
  readonly setVideoUrls: (urls: string[]) => void;
}

export function YouTubeConfig({ videoUrls, setVideoUrls }: YouTubeConfigProps) {
  return (
    <>
      <ArrayInput
        label="Video URLs *"
        values={videoUrls}
        onChange={setVideoUrls}
        placeholder="https://www.youtube.com/watch?v=..."
        helpText="YouTube video URLs to extract and distill transcripts from"
      />
      <div className="p-3 bg-blue-50 border border-blue-200 rounded-md">
        <p className="text-sm text-blue-800">
          💡 Transcripts will be automatically distilled using LLM to extract
          key concepts and technical Q&A
        </p>
      </div>
    </>
  );
}
