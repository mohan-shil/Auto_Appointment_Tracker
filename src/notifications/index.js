import notifier from 'node-notifier';
export function notifyApplicant(title,message){notifier.notify({title,message,wait:false});}
