import {z} from 'zod';

const citationSchema=z.object({
 id:z.number().int().positive(),title:z.string(),page:z.number().int().positive().nullable(),
 url:z.string().nullable(),caution:z.string().nullish(),label:z.string().nullish(),
 csv_row:z.number().nullable().optional(),course_code:z.string().nullish(),
});
const answerSchema=z.object({answer:z.string().min(1),citations:z.array(citationSchema),kind:z.string()});
export type Citation=z.infer<typeof citationSchema>;
export const unavailable='الخادم غير متاح مؤقتًا أو يعيد التشغيل. سؤالك محفوظ في خانة الكتابة؛ حاول إرساله مرة ثانية.';

export async function readChatResponse(response:Response){
 const text=await response.text();
 if(!text.trim())throw Error(unavailable);
 let data:unknown;
 try{data=JSON.parse(text);}catch{throw Error(response.status>=500?unavailable:'وصل رد غير مكتمل من الخادم. حاول إرسال السؤال مرة ثانية.');}
 if(!response.ok){
  if(response.status>=500)throw Error(unavailable);
  throw Error('تعذر قبول الطلب. راجع السؤال وحاول مرة ثانية.');
 }
 const result=answerSchema.safeParse(data);
 if(!result.success)throw Error('وصل رد غير مكتمل من الخادم. حاول إرسال السؤال مرة ثانية.');
 return result.data;
}
